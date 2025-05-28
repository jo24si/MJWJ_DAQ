import RPi.GPIO as g
import time

g.setmode(g.BCM)
g.setup(16,g.OUT)
g.setup(20,g.OUT)
g.setup(21,g.OUT)

try:
    while 1:
        g.output(16,g.HIGH)
        g.output(20,g.HIGH)
        g.output(21,g.HIGH)
        time.sleep(0.1)
        g.output(16,g.LOW)
        g.output(20,g.LOW)
        g.output(21,g.LOW)
        time.sleep(0.1)
        
except KeyboardInterrupt:
    pass
    
g.cleanup()