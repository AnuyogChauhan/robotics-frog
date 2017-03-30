## @file enswr.py ENS Workload Runtime Library Python API
#
#  Project Edge
#  Copyright (C) 2016-17  Deutsche Telekom Capital Partners Strategic Advisory LLC
#

## @page py-workload-runtime Python Workload Runtime
#
#  The @ref enswr.py "enswr" module provides the interface to the ENS Workload Runtime for
#  Python workloads.  The interface provides the workload with APIs for
#
#  -   receiving session lifecycle and data transfer events from clients and/or
#      other workloads
#  -   establishing sessions with other workloads (@ref enswr.session_start "session_start")
#  -   transfering data to clients and other workloads (@ref session_request and @ref session_notify)
#  -   managing the lifecycle of sessions (@ref session_end).
#
#  Following sections provide more details on API.
#
#  Sessions and Session Lifecycle
#  ------------------------------
#
#  Sessions are established between client and workloads in an application for the
#  purpose of exchanging data with low latency.  Establishing a session allows communication
#  channels and other initialization to be put in place up front and reused for multiple
#  data exchanges in order to achieve ultra low latency data transfers.
#
#  From the perspective of a workload, sessions may be incoming or outgoing.  An incoming
#  session is started by the runtime calling the event function associated with the
#  relevant event interface with event_type set to SESSION_START.  An outgoing
#  session is started by the workload calling session_start specifying the target
#  event interface for the session.
#
#  Sessions are identified by a unique session identifier.  This identifier has
#  local significance - the workload or client at the other end of the session does
#  not see the same session identifier.  If the application requires exchange of a shared
#  session identification then it should exchange this using a data transfer API after
#  the session is established.  The ENS session identifier is used to identify the
#  session in usage reporting.
#
#  Sessions are terminated when either end of the session calls session_end (or the
#  equivalent for the appropriate workload or client runtime), or if the underlying
#  communication channel fails.
#
#  Data Transfer
#  -------------
#
#  The API provides two mechanisms for data transfer - two-way Request/Response
#  transactions, or one-way Notify transactions.
#
#  Request/Response transactions are initiated with the session_request API (or
#  the equivalent in a different workload runtime or client runtime) and result in
#  a call to the event function with event_type set to REQUEST.
#
#  Notify transactions are initiated with the session_notify API (or equivalent)
#  and result in a call to the event function with event_type set to NOTIFY.
#
#  Threading
#  ---------
#
#  The runtime uses a dynamically sized thread pool to invoke workload event functions
#  so workloads are free to make blocking calls (to the ENS API or other system APIs)
#  without risking thread starvation in the runtime.  Workloads may also create their
#  own threads to invoke ENS API functions.
#
#  In general, event functions must be thread safe as the runtime may invoke the same
#  event function with the same session identifier concurrently with different events.
#

## @package enswr ENS Workload Runtime Library Python API
#

import threading
import traceback
import socket
import json
import time
import logging
import ensiwc


# Constants for data transfer events
REQUEST  = 0
NOTIFY   = 1
RESPONSE = 2

# Constants for session lifecycle events
SESSION_START      = 10
SESSION_STARTED    = 11
SESSION_END        = 20
SESSION_DISCONNECT = 21

__runtime = None

## Starts a new session with the named interface on another workload in the hosted
#  application.
#
#  @param  interface       Target interface name in the form &lt;microservice&gt;.&lt;interface&gt;.
#  @param  event_fn        Event function for session lifecycle and notify events on this session.
#                          If None is specified, the first event function defined on the workload
#                          is used. (Default is None.)
#  @return                 Unique identifier for the session.
#
def session_start(interface, event_fn=None):
    session = __runtime.session()
    try:
        session.start(interface, event_fn)
        return session.id
    except:
        __runtime.remove_session(session.id)
        raise

## Ends the event session.
#
#  @param  session_id      Unique identifier for the session.
#
def session_end(session_id):
    __runtime.session(session_id).end()
    __runtime.remove_session(session_id)

## Aborts the event session.
#  @deprecated
#
#  @param  session_id      Unique identifier for the session.
#  @param  reason          Reason code for the session abort.
#  @param  info            Optional text explanation of the reason for the abort.
#
def session_abort(session_id, reason, info):
    pass

## Sends a request on the event session and blocks waiting for a response.
#
#  @param  session_id      Unique identifier for the session.
#  @param  sqn             Sequence number for the request.
#  @param  data            String containing data to send in request.
#  @return                 String containing data from the response (or None if session
#                          fails).
#
def session_request(session_id, sqn, data):
    return __runtime.session(session_id).send_request(sqn, data)

## Sends a notify on the event session.
#
#  @param  session_id      Unique identifier for the session.
#  @param  sqn             Sequence number for the request.
#  @param  data            String containing data to send in notify.
#
def session_notify(session_id, sqn, data):
    __runtime.session(session_id).send_notify(sqn, data)

class ENSError(Exception):
    def __init__(self, reason):
        self.reason = reason

    def __str__(self):
        return "ENSError: %s" % self.reason

class ENSSession:
    def __init__(self, runtime, session_id):
        self.runtime = runtime
        self.id = session_id
        self.event_fn = None
        self.pending_req = {}
        self.active = False

    def start(self, interface_name, event_fn):
        if self.active:
            raise ENSError("session_start error - session already active")

        if event_fn:
            self.event_fn = event_fn
        else:
            # Get the default event function for the workload
            self.event_fn = self.runtime.event_fn("")
        w = [threading.Event(), None]
        self.pending_req[0] = w
        logging.debug("Send START(%s) for session %d" % (interface_name, self.id))
        self.runtime.send(self.id, ensiwc.MSG_SESSION_START, 0, interface_name)
        w[0].wait()
        rsp = w[1]
        del self.pending_req[0]
        logging.debug("Received STARTED for session %d (%d)" % (self.id, self.active))
        return

    def send_request(self, sqn, data):
        if not self.active:
            raise ENSError("send_request error - session inactive")

        w = [threading.Event(), None]
        self.pending_req[sqn] = w
        self.runtime.send(self.id, ensiwc.MSG_REQUEST, sqn, data)
        w[0].wait()
        rsp = w[1]
        del self.pending_req[sqn]
        return rsp

    def send_notify(self, sqn, data):
        if not self.active:
            raise ENSError("send_notify error - session inactive")

        self.runtime.send(self.id, ensiwc.MSG_NOTIFY, sqn, data)

    def end(self):
        self.disconnect()
        self.runtime.send(self.id, ensiwc.MSG_SESSION_STOP, 0, "")

    def process_msg(self, msg_id, sqn, data):
        try:
            if msg_id == ensiwc.MSG_REQUEST:
                logging.debug("Received request: %s" % data)
                rsp = self.event_fn(self.id, REQUEST, sqn, data)
                logging.debug("Sending response: %s" % rsp)
                self.runtime.send(self.id, ensiwc.MSG_RESPONSE, sqn, rsp)
            elif msg_id == ensiwc.MSG_NOTIFY:
                logging.debug("Received notify: %s" % data)
                self.event_fn(self.id, NOTIFY, sqn, data)
            elif msg_id == ensiwc.MSG_RESPONSE:
                w = self.pending_req[sqn]
                w[1] = data
                w[0].set()
            elif msg_id == ensiwc.MSG_SESSION_START:
                logging.info("Received START message")
                self.active = True
                self.event_fn = self.runtime.event_fn(data)
                self.event_fn(self.id, SESSION_START, sqn, None)
                self.runtime.send(self.id, ensiwc.MSG_SESSION_STARTED, sqn, "");
            elif msg_id == ensiwc.MSG_SESSION_STARTED:
                self.active = True
                w = self.pending_req[0]
                w[0].set()
            elif msg_id == ensiwc.MSG_SESSION_STOP:
                logging.info("Received STOP message")
                self.disconnect()
                self.event_fn(self.id, SESSION_END, sqn, None)
            elif msg_id == ensiwc.MSG_SESSION_DISCONNECTED:
                logging.info("Received DISCONNECTED message")
                self.disconnect()
                self.event_fn(self.id, SESSION_DISCONNECT, sqn, None)
        except Exception as e:
            logging.error("Exception processing message: %s" % e)
            traceback.print_exc()
            if self.active:
                self.disconnect()
                self.runtime.send(self.id, ensiwc.MSG_SESSION_STOP, 0, "")

        if not self.active:
            self.runtime.remove_session(self.id)

    def disconnect(self):
        self.active = False
        for w in self.pending_req.itervalues():
            w[1] = ""
            w[0].set()


class ENSReactor:
   class Thread(threading.Thread):
       def __init__(self, runtime):
           threading.Thread.__init__(self)
           self.runtime = runtime
           self.daemon = True
           self.start()

       def run(self):
           logging.info("New reactor thread")
           while True:
               try:
                   self.runtime.poll()
               except Exception as e:
                   logging.error("Uncaught exception in reactor poll: %s" % e)
                   traceback.print_exc()
                   break

           logging.info("Reactor thread terminated")

   def __init__(self, runtime):
       self.runtime = runtime
       self.threads = []

   def start_thread(self):
       self.threads.append(ENSReactor.Thread(self.runtime))


class ENSWorkloadRuntime:
    def __init__(self, config):
        # Parse the configuration to get the id for the shared memory interface
        # and link to the event functions
        config = json.loads(config)
        logging.debug("id = %d" % config["id"])
        self.shmid = config["id"]
        self.events = {}

        for event in config["events"]:
            mod, fn = event["fn"].rsplit('.', 1)
            self.events["%s.%s" % (config["microservice"],event["name"])] = getattr(__import__(mod), fn);

        # Set up a default event function for incoming notifies on outgoing
        # sessions.
        self.events[""] = self.events.itervalues().next()

        self.lock = threading.Lock()
        self.next_session_id = 1
        self.sessions = {}
        self.last_active = time.time()

    def run(self):
        self.iwc = ensiwc.Workload(self.shmid, 10, 100000);
        self.reactor = ENSReactor(self)
        self.reactor.start_thread()

        while True:
            time.sleep(1)

        logging.info("Exiting workload")

    def poll(self):
        (session_id, msg_id, sqn, data) = self.iwc.recv()
        logging.debug("Receive message %d, session=%d, sqn=%d, data=%s" % (msg_id, session_id, sqn, data))
        if msg_id == ensiwc.MSG_WORKLOAD_TERMINATED:
            logging.debug("Workload terminated")
            raise ENSError("Workload terminating")

        logging.debug("Check number of threads waiting")
        if self.iwc.waiters() == 0:
            # Create a new thread in the reactor
            self.reactor.start_thread()

        logging.debug("Find session")
        session = self.session(session_id)
        logging.debug("Process message")
        session.process_msg(msg_id, sqn, data)

    def send(self, session_id, msg_id, sqn, data):
        self.iwc.send(session_id, msg_id, sqn, data)

    def idle(self):
        return not self.sessions and (time.time() - self.last_active) > 10

    def session(self, session_id=None):
        if not session_id:
            session_id = self.new_session_id()

        try:
            session = self.sessions[session_id]
        except KeyError:
            session = ENSSession(self, session_id)
            self.sessions[session_id] = session

        return session

    def new_session_id(self):
        with self.lock:
            session_id = self.next_session_id
            self.next_session_id += 1
        return session_id

    def remove_session(self, session_id):
        logging.debug("Removing session %d" % session_id)
        del self.sessions[session_id]
        logging.debug("%d sessions remaining" % len(self.sessions))
        if not self.session:
            self.last_active = time.time()

    def event_fn(self, interface_name):
        try:
            return self.events[interface_name]
        except KeyError:
            raise ENSError("Unknown interface name %s" % interface_name)

def run(config):
    global __runtime
    __runtime = ENSWorkloadRuntime(config)
    __runtime.run()

