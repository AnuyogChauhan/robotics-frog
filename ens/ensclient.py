## @file ensclient.py ENS Client Runtime Library Python API
#
# Project Edge
# Copyright (C) 2016-17  Deutsche Telekom Capital Partners Strategic Advisory LLC
#

import logging
import asyncore, socket
import httplib, requests
import struct
import time
import threading
import Queue
import json
import re
import uuid


logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)-15s %(levelname)-8s %(filename)-16s %(lineno)4d %(message)s')

class ENSClientError(Exception):
    ## Exception thrown for ENS specific errors.
    def __init__(self, reason):
        self.reason = reason

    def __str__(self):
        return "ENSClientError: %s" % self.reason


class ENSEndpoint:
    def __init__(self, endpoint):
        #import pdb;pdb.set_trace()
        m = re.match(r'^(tcp|udp|http|https)://\[?([0-9]+(?:\.[0-9]+){3}|[0-9a-fA-F]{4}(?:[\:]+[0-9a-fA-F]{4}){0,7}[\:]*|[a-zA-Z0-9\-\.]+)\]?:([0-9]+)$', endpoint)
        if not m:
            raise ENSClientError("Invalid endpoint %s" % endpoint)
        self.endpoint = m.group(0)
        self.protocol = m.group(1)
        self.host = m.group(2)
        self.port = int(m.group(3))
        self.sa = [r[4] for r in socket.getaddrinfo(self.host, self.port, 0, socket.SOCK_STREAM) if r[0] == socket.AF_INET or r[0] == socket.AF_INET6]


## Class representing a session with a microservice instance hosted on the ENS platform.
#
#  This class should not be instantiated directly by client application.  Instead use the ENSClient.connect method to create a session.
#
class ENSSession(threading.Thread):

    # Data transfer message identifiers
    REQUEST  = 0
    NOTIFY   = 1
    RESPONSE = 2

    # Session lifecycle message identifiers
    START        = 10
    STARTED      = 11
    STOP         = 20
    DISCONNECTED = 21

    header = struct.Struct('>I I I')

    def __init__(self, app, cloudlet, interface, binding):
        threading.Thread.__init__(self)
        logging.info("Create ENSSession to interface %s on application %s" % (interface, app))
        self.app = app
        self.cloudlet = cloudlet
        self.interface = interface
        self.binding = binding
        self.conn = None
        self.req_sqn = 0
        self.pending_req = {}
        self.notify_q = Queue.Queue()

    def run(self):
        while True:
            # Receive the next header and any associated data.
            data = self.conn.recv(ENSSession.header.size)
            logging.debug("Received header, length %d" % len(data))
            if len(data) < ENSSession.header.size:
                break;

            length, msg_id, sqn = ENSSession.header.unpack(data)
            logging.debug("Received length %d, msg_id %d, sqn %d" % (length, msg_id, sqn))

            if length > 0:
                logging.debug("Waiting for data, length = %d", length);
                s = self.conn.recv(length)
                logging.debug("Received data, length = %d", len(s))
                if len(s) < length:
                    break;

            if msg_id == ENSSession.RESPONSE:
                # Response, so correlate to the pending request.
                logging.debug("Received response")
                if sqn in self.pending_req:
                    logging.debug("Correlated response, so unblock request sender")
                    waiter = self.pending_req[sqn]
                    waiter[1] = s
                    waiter[0].set()
                else:
                    logging.warn("Received unknown response (sqn=%d)" % sqn)
            elif msg_id == ENSSession.NOTIFY:
                # Notify, so add to the lists of pending
                logging.debug("Add Notify to queue")
                self.notify_q.put((sqn, s))
            else:
                logging.warn("Unknown message %d" % msg_id)

        logging.info("Receive loop terminated")
        self.conn.close()
        self.conn = None

    def connect(self):
        # Connect to port in the interface binding.
        #import pdb;pdb.set_trace()
        logging.info("Connecting to ENS interface %s at %s" % (self.interface, self.binding))
        try:
            eventEndpoint = ENSEndpoint(self.binding['endpoint'])
            sa = eventEndpoint.sa[0]
            self.conn = socket.create_connection( sa )
            self.conn.send(ENSSession.header.pack(len(self.interface), ENSSession.START, 0) + self.interface)
            rsp = ENSSession.header.unpack(self.conn.recv(ENSSession.header.size))
            logging.info("Session connected")
            self.start()
            return True
        except ENSClientError as e:
            logging.error("Invalid interface binding %s" % self.binding)
            return False
        except socket.error as e:
            logging.error("Failed to connect session: %s" % e)
            return False

    ## Sends a Request over the session and return the Response as a string.
    #
    #  @param  s           A string containing the request data.
    #  @return             A string containing the response data (or None if the request fails).
    def request(self, s):
        if self.conn:
            req_sqn = ++self.req_sqn
            waiter = [threading.Event(), None]
            self.pending_req[req_sqn] = waiter
            self.conn.sendall(ENSSession.header.pack(len(s), ENSSession.REQUEST, req_sqn) + s)
            waiter[0].wait()
            rsp = waiter[1]
            del self.pending_req[req_sqn]
            return rsp;
        else:
            return None

    ## Sends a Notify over the session.
    #
    #  @param  sqn         A sequence number.  This does not have to be increasing or even unique,
    #                      but can be used by the application to correlate or sequence notifys sent
    #                      in each direction.
    #  @param  s           A string containing the request data.
    #
    def notify(self, sqn, s):
        if self.conn:
            self.conn.sendall(ENSSession.header.pack(len(s), ENSSession.NOTIFY, sqn) + s)

    ## Gets Notifys received over the session.
    #
    #  @param  block       Specifies whether the call should block if no Notifys are available in the
    #                      queue (defaults to True).
    #  @param  timeout     If block is True, specifies an optional period (in seconds) to wait for a Notify to arrive.
    #  @return             A tuple containing the sequence number of the Notify and a string
    #                      containing the data.  If no Notify is available, returns None.
    #
    def get_notify(self, block=True, timeout=None):
        try:
            return self.notify_q.get(block, timeout)
        except Queue.empty:
            return None
    ## Terminates the session.
    #
    def close(self):
        logging.info("Closing session")
        if self.conn:
            self.conn.send(ENSSession.header.pack(0, ENSSession.STOP, 0))
            self.conn.shutdown(socket.SHUT_RDWR)
            #self.conn.close()
            #self.conn = None

    ## Destructor.
    #
    def __del__(self):
        self.close()


## TODO:
# 1. Add support for http methods other then GET.
#
class ENSHttpSession():

    def __init__(self, app, cloudlet, interface, binding):
        logging.info("Create ENSHttpSession to interface %s on application %s" % (interface, app))
        self.app = app
        self.cloudlet = cloudlet
        self.interface = interface
        self.binding = binding

    def connect(self):
        # Connect to port in the interface binding.
        logging.info("Connecting to HTTP interface %s at %s" % (self.interface, self.binding))
        return True

    def request(self, method, api, data):
        headers = {'content-type': 'application/json','API-KEY': self.binding['accessToken']}
        url = self.binding['endpoint'] + api
        if method == 'get':
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                rsp = json.loads(response.text)
                logging.info("API response: %s" %json.dumps(rsp))
                return json.dumps(rsp)
            else:
                logging.error("Service error: [%s] - %s" %(response.status_code, response.reason));

        return None

    def close(self):
        return

    def __del__(self):
        return


class ENSNetworkSession():
    def __init__(self, app, cloudlet, interface, binding):
        logging.info("Create ENSNetworkSession to interface %s on application %s" % (interface, app))
        self.app = app
        self.cloudlet = cloudlet
        self.interface = interface
        self.binding = binding
        self.conn = None
        self.rfile = None

    def connect(self):
        # Connect to port in the interface binding.
        logging.info("Connecting to Network interface %s at %s" % (self.interface, self.binding))
        try:
            nwEndpoint = ENSEndpoint(self.binding['endpoint'])
            sa = nwEndpoint.sa[0]
            logging.debug("Connecting cloudlet at %s:%d" % (sa[0], sa[1]))
            self.conn = socket.create_connection( (sa[0], sa[1]) )
            self.rfile = self.conn.makefile("rb")
        except ENSClientError:
            logging.error("Invalid endpoint %s for %s" % (self.binding['endpoint'], self.interface))
            return False
        except socket.error:
            logging.error("Failed to connect to endpoint %s for %s" % (self.binding['endpoint'], self.interface))
            return False

        return True

    def request(self, data):
        if self.conn:
            self.conn.sendall(data)
            return self.rfile.read()
        else:
            return None

    def close(self):
        if self.rfile:
            self.rfile.close()
            self.conn.close()
            self.rfile = self.conn = None

    def __del__(self):
        self.close()


## Class representing client application.
#
#  An application should create an instance of this class then call the init() method to
#  authenticate with the ENS platform, select an appropriate cloudlet and instantiate the
#  hosted application and microservice components on that cloudlet.
#
class ENSClient():
    class Probe(asyncore.dispatcher):
        def __init__(self, cloudlet, config, app):
            asyncore.dispatcher.__init__(self)
            logging.info("Probe cloudlet %s for application %s" % (str(cloudlet), app))
            self.app = app
            self.cloudlet = cloudlet
            self.sampling = False
            self.samples = []

            if "endpoints" in config and "probe" in config["endpoints"]:
                try:
                    probe = config["endpoints"]["probe"]
                    probeEndpoint = ENSEndpoint(probe)
                    sa = probeEndpoint.sa[0]
                    logging.debug("Probe cloudlet at %s:%d" % (sa[0], sa[1]))
                    self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.connect(sa)
                except ENSClientError:
                    logging.error("Invalid probe endpoint %s for cloudlet %s" % (probe, cloudlet))
                except socket.error:
                    logging.error("Failed to connect to probe endpoint %s for cloudlet %s" % (probe, cloudlet))
                self.buffer = "ENS-PROBE %s\r\n" % self.app
            else:
                logging.error("Missing probe endpoint configuration for cloudlet %s" % cloudlet)

        def handle_connect(self):
            pass

        def handle_error(self):
            pass

        def handle_close(self):
            logging.debug("Closing probe for cloudlet %s" % self.cloudlet)
            self.close()

        def handle_read(self):
            self.end_time = time.time()
            rsp = self.recv(8192)
            logging.debug("Received (%s): %s" % (self.cloudlet, rsp))

            if not self.sampling:
                # Check that the microservice is supported
                params = rsp.splitlines()[0].split(' ')
                if params[0] == "ENS-PROBE-OK":
                    # Microservice is supported, so save microservice data
                    self.buffer = "ENS-RTT %s\r\n" % self.app
                    self.sampling = True
                else:
                    # Microservice is not supported, so just close the socket
                    # and wait for other probes to finish.
                    self.close()
            else:
                # Must be doing RTT estimation
                rtt = self.end_time - self.start_time
                logging.debug("RTT = %f" % rtt);
                self.samples.append(rtt)
                if len(self.samples) < 10:
                    self.buffer = "ENS-RTT %s\r\n" % self.app
                else:
                    logging.debug("Completed 10 RTT probes to %s" % self.cloudlet)

        def writable(self):
            return (len(self.buffer) > 0)

        def handle_write(self):
            self.start_time = time.time()
            sent = self.send(self.buffer)
            logging.debug("Sent (%s): %s" % (self.cloudlet, self.buffer))
            self.buffer = self.buffer[sent:]

        def rtt(self):
            if len(self.samples):
                return sum(self.samples) / float(len(self.samples))
            else:
                return -1

    # Microservice class; helper calls to keeps the application endpoints
    # (http, event, network) information.
    class Microservice():
        def __init__(self, ms_data):
            self._ms_name = ms_data["name"]
            self._ms_data = ms_data

            self._faas_bindings = {}
            for binding in self._ms_data["eventGateway"]:
                binding_name = self._ms_name + "." + binding["eventId"]
                self._faas_bindings[binding_name] = binding

            self._http_bindings = {}
            for binding in self._ms_data["httpGateway"]:
                binding_name = self._ms_name + "." + binding["httpApiId"]
                self._http_bindings[binding_name] = binding

            self._network_bindings = {}
            for binding in self._ms_data["networkBinding"]:
                binding_name = self._ms_name + "." + binding["networkId"]
                self._network_bindings[binding_name] = binding

        def name(self):
            return self._ms_name

        def faas_binding(self, interface):
            return self._faas_bindings[interface]

        def faas_bindings(self):
            return self._faas_bindings

        def http_binding(self, interface):
            return self._http_bindings[interface]

        def http_bindings(self):
            return self._http_bindings

        def network_binding(self, interface):
            return self._network_bindings[interface]

        def network_bindings(self):
            return self._network_bindings


    ## Constructor for ENSClient instance.
    #
    #  @param  app         Application identifier in the form <developer-id>.<app-id>.
    #
    def __init__(self, app):
        # Open the configuration file to get the Discovery Server URL, API key
        # and SDK version.
        self.sdkconfig = {}
        with open("mecsdk.conf") as sdkfile:
            logging.info("Loading MEC SDK settings")
            for line in sdkfile:
                name, var = line.partition("=")[::2]
                self.sdkconfig[name.strip()] = var.strip()
            if "DiscoveryURL" not in self.sdkconfig:
                raise ENSClientError("Missing DiscoveryURL in mecsdk.conf file")
            if "SdkVersion" not in self.sdkconfig:
                raise ENSClientError("Missing SdkVersion in mecsdk.conf file")
            if "ApiKey" not in self.sdkconfig:
                raise ENSClientError("Missing ApiKey in mecsdk.conf file")

        ## TODO:
        # Need to finalize how client-id will be generated. Options:
        # 1. Generate it once during first use of ENSClient and get it stored in the conf.
        # 2. Generate it every time ENSClient gets instantiated.
        #
        # As of now, taking the second approach.
        #
        self.client_id = str(uuid.uuid4()).replace('-', '')

        self.app = app
        self.cloudlet = ""
        self.aac = None
        self.deployment_id = None

        self.event_bindings = {}
        self.network_bindings = {}
        self.probed_rtt = 0.0

    ## Requests initialization of the hosted application on the ENS platform.
    #
    #  @return           True or False indicating success of operation.
    #
    def init(self):
        """Requests initialization of the hosted application on the ENS platform.

        Return True or False indicating success of operation.
        """
        if ("Environment" in self.sdkconfig) and (self.sdkconfig["Environment"] == "localhost"):
            # Send a service request to workload-tester to instantiate the application and microservices.
            aac = "http://127.0.0.1:8080"
            try:
                headers = {'content-type': 'application/json'}
                url = "%s/api/v1.0/workload-tester/%s/%s" %(str(aac),developer_id,app_id)
                response = requests.post(url,headers=headers)
                if response.status_code == 200:
                    data = json.loads(response.text)
                    logging.debug("Server Response ==>" + json.dumps(data))
                else:
                    logging.error("Failed to initialize application: %s" % rsp)
                    return False

                self.deployment_id = data["deploymentId"]
                self.microservices = {}
                for ms_data in data["microservices"]:
                    self.microservices[ms_data["name"]] = ENSClient.Microservice(ms_data)

                return True
            except socket.error:
                pass
        else:
            # Contact the Discovery Server to get a candidate list of cloudlets for the app
            # and the contact details for the app@cloud instance.
            dr = {}
            developer_id, app_id = self.app.split('.')
            response = requests.get("%s/api/v1.0/discover/%s/%s?sdkversion=%s" % (self.sdkconfig["DiscoveryURL"], developer_id, app_id, self.sdkconfig["SdkVersion"]), headers = {"Authorization": "Bearer %s" % self.sdkconfig["ApiKey"]})

            if response.status_code == httplib.OK:
                dr = json.loads(response.content)

            logging.debug("Discovery server response:\n%s" % dr)

            if "cloudlets" not in dr:
                logging.error("No cloudlets element in Discovery Server response")
                return False

            if "cloud" not in dr or "endpoints" not in dr["cloud"] or "app@cloud" not in dr["cloud"]["endpoints"]:
                logging.error("No app@cloud element in Discovery Server response")
                return False

            cloudlets = dr["cloudlets"]
            self.aac = str(dr["cloud"]["endpoints"]["app@cloud"])

            if len(cloudlets) == 0:
                logging.error("No cloudlets to probe")
                return False

            # Create probes for each cloudlet
            logging.debug("Probe %d cloudlets" % len(cloudlets))
            probes = [ENSClient.Probe(c, v, self.app) for c,v in cloudlets.iteritems()]

            # Run the probes for one second
            start = time.time()
            while (time.time() - start) < 1:
                asyncore.loop(timeout=1, count=1, use_poll=True)

            logging.info("Probes completed");
            for probe in probes:
                probe.close()

            # Pick the probe with the shortest RTT
            rtts = [(p.rtt(), p.cloudlet) for p in probes if p.rtt() != -1]
            rtts = sorted(rtts, key=lambda p: p[0])
            logging.debug(repr(rtts))

            if len(rtts) == 0:
                return False

            self.cloudlet = rtts[0][1]
            self.probed_rtt = rtts[0][0]

            # Send a service request to platform app@cloud to instantiate the application and microservices.
            try:
                headers = {'content-type': 'application/json'}
                url = "%s/api/v1.0/app_cloud/%s/%s/%s/%s" %(self.aac, developer_id, app_id, self.cloudlet, self.client_id)
                response = requests.post(url,headers=headers)
                print response.text
                if response.status_code == 200:
                    data = json.loads(response.text)
                else:
                    logging.error("Failed to initialize application: %s" % response)
                    return False

                self.deployment_id = data["deploymentId"]
                self.microservices = {}
                for ms_data in data["microservices"]:
                    self.microservices[ms_data["name"]] = ENSClient.Microservice(ms_data)

                return True

            except socket.error:
                pass

        return False

    ## Requests connection of a session to the specified interface provided by the hosted application.
    #
    #  @param interface    Interface name in the form &lt;microservice&gt;.&lt;interface&gt;.
    #  @return             An ENSSession/ENSHttpSession/ENSNetworkSession object (or None if the session cannot be connected).
    #
    def connect(self, interface):
        ms_name = interface.split('.')[0]
        if ms_name not in self.microservices:
            return None

        ms = self.microservices[ms_name]

        if interface in ms.faas_bindings():
            # Create an ENSSession object for the connection
            session = ENSSession(self.app, self.cloudlet, interface, ms.faas_binding(interface))
            if session.connect():
                return session
            else:
                return None

        if interface in ms.http_bindings():
            # Create an ENSHttpSession object for the connection
            session = ENSHttpSession(self.app, self.cloudlet, interface, ms.http_binding(interface))
            if session.connect():
                return session
            else:
                return None

        if interface in ms.network_bindings():
            # Create an ENSNetworkSession object for the connection
            session = ENSNetworkSession(self.app, self.cloudlet, interface, ms.network_binding(interface))
            if session.connect():
                return session
            else:
                return None

        logging.error("Cannot connect to unknown interface %s" % interface)
        return None

    def close(self):
        developer_id, app_id = self.app.split('.')
        headers = {'content-type': 'application/json'}
        url = "%s/api/v1.0/app_cloud/%s/%s/%s/%s/%s" %(self.aac, developer_id, app_id, self.cloudlet, self.client_id, self.deployment_id["uuid"])
        print url
        response = requests.delete(url,headers=headers)
        if response.status_code == 200:
            logging.debug("Application '%s' with deployment id '%s' deleted successfully !!" %(app_id, self.deployment_id["uuid"]))
        else:
            logging.debug("Failed to deleted Application '%s' with deployment id '%s' !!" %(app_id, self.deployment_id["uuid"]))

    def __del__(self):
        self.close()
