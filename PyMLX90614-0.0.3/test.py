import RPi.GPIO as GPIO 
import picamera
import time
 
import smtplib
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from email.MIMEBase import MIMEBase
from email import encoders
from email.mime.image import MIMEImage
 
from smbus2 import SMBus
from mlx90614 import MLX90614
 
GPIO.setmode(GPIO.BCM)
GPIO.setup(17, GPIO.OUT)
GPIO.setup(22, GPIO.OUT)

fromaddr = "ec1772017@gmail.com"    # change the email address accordingly
toaddr = "surajpandeydn@gmail.com"
 
mail = MIMEMultipart()
 
mail['From'] = fromaddr
mail['To'] = toaddr
mail['Subject'] = "IOT BASED THERMAL SCREENING"
body = "Temperature Alert..\nPlease find the attached image"
 
data=""
 
def sendMail(data):
    mail.attach(MIMEText(body, 'plain'))
    print data
    dat='%s.jpg'%data
    print dat
    attachment = open(dat, 'rb')
    image=MIMEImage(attachment.read())
    attachment.close()
    mail.attach(image)
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(fromaddr, "Suraj@123")
    text = mail.as_string()
    server.sendmail(fromaddr, toaddr, text)
    server.quit()
 
def capture_image():
    data= time.strftime("%d_%b_%Y|%H:%M:%S")
    camera.start_preview()
    print data
    camera.capture('%s.jpg'%data)
    camera.stop_preview()
    time.sleep(0.1)
    GPIO.output(17, False) 
    sendMail(data)

camera = picamera.PiCamera()
camera.rotation=0
camera.awb_mode= 'auto'
camera.brightness=55
 
while 1:
    bus = SMBus(1)
    sensor = MLX90614(bus, address=0x5A)
    print "Ambient Temperature :", sensor.get_ambient()
    print "Object Temperature :", sensor.get_object_1()
    temp = sensor.get_object_1()
    bus.close()
    if temp>37:
        GPIO.output(17, True)
        GPIO.output(22, False) 
	body += "\nThe temprature was found to be " + str(temp * 1.8 + 32)+" F" 
	capture_image()
	time.sleep(0.1)
    else:
        GPIO.output(17, False)
        GPIO.output(22, True) 
	time.sleep(0.01)
GPIO.cleanup()
