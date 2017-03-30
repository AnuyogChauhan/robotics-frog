
from concurrent import futures
import grpc
import time
import messages_pb2
import messages_pb2_grpc

from robotcalc import getAngleDistance

class ServePosition(messages_pb2_grpc.PositionFinderServicer):

    def GetPosition(self, request, context):
        if( request.x < 0 or request.y < 0 or request.y > 1 or request.x > 1):
          return messages_pb2.ArmPosition(base=0,shoulder=0,error=True,message="field position out of bounds")
        base1,shoulder1 = getAngleDistance(request.x, request.y, request.inverted)
        return messages_pb2.ArmPosition(base=base1, shoulder=shoulder1, error=False,message="")

def serve():
    server = grpc.server( futures.ThreadPoolExecutor(max_workers=10) )
    messages_pb2_grpc.add_PositionFinderServicer_to_server(ServePosition(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    try:
      while True:
        time.sleep( 60 * 60 * 24 )
    except KeyboardInterrupt:
      server.stop(0)

if __name__ == "__main__":
    serve()
