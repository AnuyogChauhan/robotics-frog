#
# @file enswmain.py
#
# Project Edge
# Copyright (C) 2016-17  Deutsche Telekom Capital Partners Strategic Advisory LLC
#

import sys, logging
import enswr

if len(sys.argv) == 1:
    print("Usage: %s <config>" % sys.argv[0])
    sys.exit(1)

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)-15s %(levelname)-8s %(filename)-16s %(lineno)4d %(message)s')

enswr.run(sys.argv[1])
logging.debug("Calling sys.exit(0)")
sys.exit(0)
