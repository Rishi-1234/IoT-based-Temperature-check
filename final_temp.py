from gpiozero import LED
red = LED(17)
green = LED(22)

from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
from tensorflow.keras.preprocessing.image import img_to_array
from tensorflow.keras.models import load_model
from imutils.video import VideoStream
import RPi.GPIO as gpio
from smbus2 import SMBus
from mlx90614 import MLX90614
import smtplib, ssl
from email.mime.multipart import MIMEMultipart
from email import encoders
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
import numpy as np
import argparse
import imutils
import time
import cv2
import os

final_temp = 0
photoTime = ''

def detect_and_predict_mask(frame, faceNet, maskNet):
	(h, w) = frame.shape[:2]
	blob = cv2.dnn.blobFromImage(frame, 1.0, (300, 300), (104.0, 177.0, 123.0))

	faceNet.setInput(blob)
	detections = faceNet.forward()

	faces = []
	locs = []
	preds = []

	for i in range(0, detections.shape[2]):
		confidence = detections[0, 0, i, 2]

		if confidence > args["confidence"]:
			box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
			(startX, startY, endX, endY) = box.astype("int")
			(startX, startY) = (max(0, startX), max(0, startY))
			(endX, endY) = (min(w - 1, endX), min(h - 1, endY))

			face = frame[startY:endY, startX:endX]
			face = cv2.cvtColor(face, cv2.COLOR_BGR2RGB)
			face = cv2.resize(face, (224, 224))
			face = img_to_array(face)
			face = preprocess_input(face)

			faces.append(face)
			locs.append((startX, startY, endX, endY))

	if len(faces) > 0:
		faces = np.array(faces, dtype="float32")
		preds = maskNet.predict(faces, batch_size=32)

	return (locs, preds)

ap = argparse.ArgumentParser()
ap.add_argument("-f", "--face", type=str, default="face_detector", help="path to face detector model directory")
ap.add_argument("-m", "--model", type=str, default="mask_detector.model", help="path to trained face mask detector model")
ap.add_argument("-c", "--confidence", type=float, default=0.5, help="minimum probability to filter weak detections")
args = vars(ap.parse_args())

print("[INFO] loading face detector model...")
prototxtPath = os.path.sep.join([args["face"], "deploy.prototxt"])
weightsPath = os.path.sep.join([args["face"], "res10_300x300_ssd_iter_140000.caffemodel"])
faceNet = cv2.dnn.readNet(prototxtPath, weightsPath)

print("[INFO] loading face mask detector model...")
maskNet = load_model(args["model"])

print("[INFO] starting video stream...")
vs = VideoStream(usePiCamera=True, rotation=180, brightness=55).start()
time.sleep(3.0)

def start_camera():
	flag = 0
	while True:
		frame = vs.read()
		frame = imutils.resize(frame, width=500)
	
		(locs, preds) = detect_and_predict_mask(frame, faceNet, maskNet)

		for (box, pred) in zip(locs, preds):
			(startX, startY, endX, endY) = box
			(mask, withoutMask) = pred
		
			if mask > withoutMask:
				label = "Mask Detected"
				color = (0, 255, 0)
				red.off()
				flag += 1
			else:
				label = "No Face Mask Detected"
				color = (0, 0, 255)
				green.off()
				red.on()

			cv2.putText(frame, label, (startX-50, startY - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
			cv2.rectangle(frame, (startX, startY), (endX, endY), color, 2)

		cv2.imshow("Face Mask Detector", frame)
		time.sleep(1.0)
		key = cv2.waitKey(1) & 0xFF

		if flag >= 7:
			global photoTime
			photoTime = time.strftime("%Y-%m-%d-%H:%M")
			cv2.imwrite("/home/pi/temp_monitoring/FaceMask/face_images/"+photoTime+".jpg", frame)
			return True
			
		if key == ord("q"):
			return False

def check_temperature():
	flag = 0
	global final_temp
	while True:
		bus = SMBus(1)
		sensor = MLX90614(bus, address=0x5A)
		print("Ambient Temperature :", sensor.get_ambient())
		print("Object Temperature :", sensor.get_object_1())
		temp = sensor.get_object_1()
		final_temp = temp
		bus.close()
		if temp<37:
			flag += 1
			time.sleep(0.1)
		else:
			return False
			
		if flag >= 25:
				return True
				
def sendMail():
	receiver_email = 'surajpandeydn@gmail.com'
	print('Sending Email to: ', receiver_email)
	sender_email = 'ec1772017@gmail.com'
	password = 'Suraj@123'

	message = MIMEMultipart("alternative")
	message["Subject"] = "Alert: IOT BASED TEMPRATURE SCREENING"
	message["From"] = receiver_email
	message["To"] = sender_email

	with open('face_images/' + photoTime + '.jpg', 'rb') as f:
		mime = MIMEBase('image', 'jpg', filename = photoTime + '.jpg')
		mime.add_header('Content-Disposition', 'attachment', filename = photoTime + '.jpg')
		mime.add_header('X-Attachment-Id', '0')
		mime.add_header('Content-ID', '<0>')
		mime.set_payload(f.read())
		encoders.encode_base64(mime)
		message.attach(mime)

	body = MIMEText('''
	<html>
		<body>
			<h1>Alert</h1>
			<h2>A new person was not allowed to enter building</h2>
			<h2>Body Temperature: {} &#8457; </h2>
			<h2>Mask: Wearing</h2>
			<h2>Time: {}</h2>
			<p>
				<img src="cid:0">
			</p>
		</body>
	</html>'''.format(((final_temp * 1.8) + 32),time.strftime("%Y-%m-%d-%H:%M")), 'html', 'utf-8')

	message.attach(body)

	context = ssl.create_default_context()
	with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
		server.login(sender_email, password)
		server.sendmail(
			receiver_email, sender_email, message.as_string()
		)

flag_mask = False
flag_temp = False

while True:
	flag_mask = start_camera()
	cv2.destroyAllWindows()
	vs.stop()
	
	if flag_mask == True:
		print("Ready to Read Temperature")
		time.sleep(2.0)
		flag_temp == check_temperature()
		
		if flag_temp == True:
			red.off()
			time.sleep(5.0)
			green.on()
			print("You can Proceed.. Thankyou..")
			time.sleep(5.0)
			break
		else:
			print("Sending Details to Admin")
			sendMail()
			red.on()
			time.sleep(2.0)
			print("Mail Send Successfully to Admin")
			print("You cannot proceed as your temprature is above 98.6 F")
			break			
	else:
		print("Sorry You were not wearing mask..")
		break

red.off()
green.off()
