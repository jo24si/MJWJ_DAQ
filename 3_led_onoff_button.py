import RPi.GPIO as g
import time


ledRed=21
ledBlue=20
swPin=12
buzzer=7

g.setmode(g.BCM)
g.setup(ledRed,g.OUT)
g.setup(ledBlue,g.OUT)
g.setup(buzzer,g.OUT)
g.setup(swPin,g.IN, pull_up_down=g.PUD_DOWN)

try:
    while 1:
        swValue=g.input(swPin)
        if swValue :
            g.output(buzzer,g.HIGH)
        else :
            g.output(buzzer,g.LOW)
    
        print(swValue)
        time.sleep(0.1)
        
        
except KeyboardInterrupt:
    pass
    
g.cleanup()
