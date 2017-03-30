import json
import enswr
from robotcalc import getAngleDistance


# Event handler function for simple latency test responder.
def event_handler(session_id, event_type, sqn, data):
    if event_type == enswr.REQUEST:
        req = json.loads(data)
        xval = req['x']
        yval = req['y']
        inverted = req['inverted']
        base, shoulder = getAngleDistance(xval, yval, inverted)
        response = dict()
        response['base'] = base
        response['shoulder'] = shoulder
        return json.dumps(response)
    elif event_type == enswr.NOTIFY:
        enswr.session_notify(session_id, sqn, data)

    return 
