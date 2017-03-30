

import math

def getAngleDistance(xp2, yp2, inverse=False):
    yMeasure = 18.25#18.25
    xMeasure = 32.0#32
    gamma = 3.5 # distance between base of arm and "field"
    epsilon = 13.0 # length of arm (approximate)
    xNorm = 0.0
    yNorm = 0.0
    #print(xp2)
    #print(yp2)
    if(inverse):
        yNorm = float(yp2)
        xNorm = (1.0 - float(xp2))
    else:
        xNorm = float(xp2)
        yNorm = (1.0 - float(yp2))
    
    b = ( yNorm * yMeasure ) + gamma

    if( b < 0 ):
        b = b * -1

    a = ( abs(xNorm - 0.5) * xMeasure) 
    c = math.sqrt( pow(a,2) + pow(b,2))
    #print("a: {0} b: {1} c: {2}".format(a,b,c))
    
    degreesFromCenter = 90
    sinA = float(a) / float(c)
    aAngle = (math.asin(sinA) * 180) / math.pi
    bAngle = 90 - aAngle
    
    if( xNorm > 0.5 ):
        degreesFromCenter = 90 - aAngle
    else:
        degreesFromCenter = 90 + aAngle
    
    d = c/(epsilon + gamma)
    if(d > 1):
        d = 1.0
        
    cAngle = 120 - (115 * d)
    return (int(degreesFromCenter),int(cAngle))
      


