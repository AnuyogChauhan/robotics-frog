# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
import grpc
from grpc.framework.common import cardinality
from grpc.framework.interfaces.face import utilities as face_utilities

import messages_pb2 as messages__pb2


class PositionFinderStub(object):

  def __init__(self, channel):
    """Constructor.

    Args:
      channel: A grpc.Channel.
    """
    self.GetPosition = channel.unary_unary(
        '/robotics.PositionFinder/GetPosition',
        request_serializer=messages__pb2.FieldPosition.SerializeToString,
        response_deserializer=messages__pb2.ArmPosition.FromString,
        )


class PositionFinderServicer(object):

  def GetPosition(self, request, context):
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')


def add_PositionFinderServicer_to_server(servicer, server):
  rpc_method_handlers = {
      'GetPosition': grpc.unary_unary_rpc_method_handler(
          servicer.GetPosition,
          request_deserializer=messages__pb2.FieldPosition.FromString,
          response_serializer=messages__pb2.ArmPosition.SerializeToString,
      ),
  }
  generic_handler = grpc.method_handlers_generic_handler(
      'robotics.PositionFinder', rpc_method_handlers)
  server.add_generic_rpc_handlers((generic_handler,))