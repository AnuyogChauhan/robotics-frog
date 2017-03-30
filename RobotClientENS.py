import json
import sys
from ens import ensclient
import time


class RobotClientENS():
    def __init__(self):
        self.identifier = "mec.robotics02"
        self.network = "micro-robot-network.ping"
        self.my_ens_client = None
        self.connection = None

    def getValues(self, xVal, yVal, inverted):
        if self.my_ens_client is None:
            self.my_ens_client = ensclient.ENSClient(self.identifier)
            
        if self.connection is None and self.my_ens_client is not None:
            if self.my_ens_client.init():
                self.connection = self.my_ens_client.connect(self.network)
            else:
                print("failed to initialize")
                sys.exit(1)
                
        if self.connection is not None:
            toRequest = dict()
            toRequest['x'] = xVal
            toRequest['y'] = yVal
            toRequest['inverted'] = inverted
            response = self.connection.request(json.dumps(toRequest))
            print response
            return response
        else:
            print "failed to connect to ar-network"
            
        return None
        

    def close(self):          
        if self.connection is not None:
            self.connection.close()
            
        if self.my_ens_client is not None:
            self.my_ens_client.close()



if __name__ == "__main__":
    start_time = time.time()
    sc = RobotClientENS()
    connection_finished = time.time()
    value1 = sc.getValues(0.5, 0.5, False)
    value_one = time.time()
    value2 = sc.getValues(0.6, 0.2, True)
    value_two = time.time()
    sc.close()
    closed = time.time()
    print("start to connection {0}".format(connection_finished - start_time))
    print("connection to value 1 {0}".format(value_one - connection_finished))
    print("value 1 to value 2 {0}".format(value_two - value_one))
    print("value 2 to closed {0}".format(closed - value_two))
   
