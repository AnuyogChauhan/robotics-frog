
import unittest
import grpc
from messages_pb2 import FieldPosition, ArmPosition
from messages_pb2_grpc import PositionFinderStub



"""
    a simple fetching function, using google protocol buffers.
    The "request" element is a field position - an X, Y value within the soccer field
    the "response" element is a set of two angles - a shoulder joint and a base joint
"""

def getPositionTraditional( fieldposition ):
    channel = grpc.insecure_channel('localhost:5001')
    stub = PositionFinderStub(channel)
    return stub.GetPosition(fieldposition)





class TestTraditionalNetwork(unittest.TestCase):
    
    """
    Given a position on the field, represented by 0.0 - 1.0 (x value) and 0.0 - 1.0 (y value), give back the two angles we care about
    for the robot arm - represented as "shoulder" and "base"
    
    Inversion is best explained that one of the arms is "upside down" relative to the field - so the angles are going to be different
    for the "inverted" arm.
    """
    def test_normalUseInverted(self):
        fp = FieldPosition(x=0.452, y=0.2402, inverted=True)
        response1 = getPositionTraditional(fp)
        self.assertEqual(response1.base, 78)
        self.assertEqual(response1.shoulder, 64)
        self.assertEqual(response1.error, False)
        self.assertEqual(response1.message,"")
    
    """
    Given a position on the field, give back the shoulder and base joint 
    """
    def test_normalUseNonInverted(self):
        fp = FieldPosition(x=0.452, y=0.2402, inverted=False)
        response1 = getPositionTraditional(fp)
        self.assertEqual(response1.base, 95)
        self.assertEqual(response1.shoulder, 5)
        self.assertEqual(response1.error, False)
        self.assertEqual(response1.message,"")
    
    """
    Error handling test 1: show what happens when you give a position of bounds on the top right of the field
        this is important because the robot arms could damage themselves if given angles outside the operational parameters
        shoulder: 120 - 5 degrees, base 30 - 150 degrees
    """
    def test_testTopRightOutOfBounds(self):
        fp = FieldPosition(x=1.1, y=0.1402, inverted=True)
        response1 = getPositionTraditional(fp)
        self.assertEqual(response1.error, True)
        self.assertEqual(response1.base, 0)
        self.assertEqual(response1.shoulder, 0)
    """
    Error handling test 2: show what happens when you give a position of bounds at the bottom right of the field
    """
    def test_testBottomLeftOutOfBounds(self):
        fp = FieldPosition(x=-0.1, y=0.1402, inverted=True)
        response1 = getPositionTraditional(fp)
        self.assertEqual(response1.error, True)
        self.assertEqual(response1.base, 0)
        self.assertEqual(response1.shoulder, 0)

class TestENSNetwork(unittest.TestCase):
    
    """
    Given a position on the field, represented by 0.0 - 1.0 (x value) and 0.0 - 1.0 (y value), give back the two angles we care about
    for the robot arm - represented as "shoulder" and "base"
    """
    def test_normalUseInverted(self):
        self.assertFalse(True)
        
    """
    Given a position on the field, give back the shoulder and base joint 
    """    
    def test_normalUseNonInverted(self):
        self.assertFalse(True)
    
    """
    Error handling test 1: show what happens when you give a position of bounds on the top right of the field
        this is important because the robot arms could damage themselves if given angles outside the operational parameters
        shoulder: 120 - 5 degrees, base 30 - 150 degrees
    """  
    def test_testTopRightOutOfBounds(self):
        self.assertFalse(True)
        
    """
    Error handling test 2: show what happens when you give a position of bounds at the bottom right of the field
    """
    def test_testBottomLeftOutOfBounds(self):
        self.assertFalse(True)
        
if __name__ == '__main__':
    unittest.main()
