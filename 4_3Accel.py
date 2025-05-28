import smbus
import time
#import board

#import busio
from PIL import Image, ImageDraw, ImageFont
import Adafruit_SSD1306




#i2c Bus Setting
BUS = smbus.SMBus(1)
ADDRESS_ADXL345=0x53 #ADXL345 I2C Addr
ADDRESS_SSD1306=0x3c

oled=Adafruit_SSD1306.SSD1306_128_64(rst=None, i2c_address=ADDRESS_SSD1306)


oled.begin()
oled.clear()
oled.display()




#ADXL345 Init Setting
def adxl345_Init():
    BUS.write_byte_data(ADDRESS_ADXL345, 0x2D,0x08)
    #power_crl : mode on
    BUS.write_byte_data(ADDRESS_ADXL345, 0x31,0x08)
    #data_format: +- 2g set
    BUS.write_byte_data(ADDRESS_ADXL345,0x2C,0x0A)
    #bw_rate : 100hz sampling speed
    
def read_acceleration():
    data=BUS.read_i2c_block_data(ADDRESS_ADXL345, 0x32,6)
    #0x32~6byte (x,y,z)
    
    x=(data[1]<<8)| data[0]
    y=(data[3]<<8)| data[2]
    z=(data[5]<<8)| data[4]
    
    #16bit change
    
    x=x-65536 if x>32767 else x
    y=y-65536 if y>32767 else y
    z=z-65536 if z>32767 else z
    
    return x,y,z

#process
adxl345_Init()


font=ImageFont.load_default()
t1=""
t2=""
t3=""

while True:
    x,y,z =read_acceleration()
    image = Image.new("1",(oled.width,oled.height))
    draw=ImageDraw.Draw(image)
    
    print(f"x:{x}, y:{y}, z:{z}")
    t3=f"x:{x}, y:{y}, z:{z}"      
    draw.text((10,10),t1,font=font, fill=255)    
    draw.text((10,25),t2,font=font, fill=255)    
    draw.text((10,40),t3,font=font, fill=255)
    
    oled.image(image)
    oled.display()
    time.sleep(0.5)
    oled.clear()
    
    t2=t3
    
    x,y,z =read_acceleration()
    image = Image.new("1",(oled.width,oled.height))
    draw=ImageDraw.Draw(image)
    
    print(f"x:{x}, y:{y}, z:{z}")
    t3=f"x:{x}, y:{y}, z:{z}" 
    draw.text((10,10),t1,font=font, fill=255)    
    draw.text((10,25),t2,font=font, fill=255)    
    draw.text((10,40),t3,font=font, fill=255)
    
    oled.image(image)
    oled.display()
    time.sleep(0.5)
    oled.clear()
    t1=t2     
