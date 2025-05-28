import RPi.GPIO as GPIO
import time

ledWhite=21

swPin=12

buzzer=7

GPIO.setmode(GPIO.BCM)
GPIO.setup(ledWhite,GPIO.OUT)
GPIO.setup(buzzer,GPIO.OUT)
GPIO.setup(swPin,GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

ledWhitePWM=GPIO.PWM(ledWhite,100)
ledWhitePWM.start(0)

try:
    while 1:
        ledWhitePWM.ChangeDutyCycle(0)
        print("Duty:0")
        time.sleep(2.0)
        ledWhitePWM.ChangeDutyCycle(30)
        print("Duty:30")
        time.sleep(2.0)
        ledWhitePWM.ChangeDutyCycle(60)
        print("Duty:60")
        time.sleep(2.0)
        ledWhitePWM.ChangeDutyCycle(100)
        print("Duty:100")
        time.sleep(2.0)
    
        
        
except KeyboardInterrupt:
    pass
    
GPIO.cleanup()