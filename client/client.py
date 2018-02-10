import datetime
import gevent
import gevent.monkey
import MySQLdb
import sys
import Adafruit_DHT
import datetime
import time
import threading
import RPi.GPIO as GPIO
import json
import boto3
from boto3.dynamodb.conditions import Key, Attr
from flask import *


from gevent.pywsgi import WSGIServer
from picamera import PiCamera
from flask import Flask, request, Response, render_template
from gpiozero import LED, MotionSensor, Buzzer, MCP3008
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient

gevent.monkey.patch_all()

DELAY = 3
pir = MotionSensor(26, sample_rate=5,queue_len=1)
bz = Buzzer(5)
camera = PiCamera()
LED_PIN = 18
GPIO.setmode(GPIO.BCM)
GPIO.setup(18, GPIO.OUT)

my_rpi = None
globaltemp = None
globalhumidity = None

def customCallbackfortemperature(client, userdata, message):
	global globaltemp
	print("Received a new message: ")
	print(message.payload)
	globaltemp = json.loads(message.payload)
	print("from topic: ")
	print(message.topic)
	print("--------------\n\n")

def customCallbackforhumidity(client, userdata, message):
	global globalhumidity
	print("Received a new message: ")
	print(message.payload)
	globalhumidity = json.loads(message.payload)
	print("from topic: ")
	print(message.topic)
	print("--------------\n\n")

#def store_alert_to_db(datetime):
#
	#try:
	#	db = MySQLdb.connect("localhost", "root", "dmitiot", "Assignment")
	#	curs = db.cursor()
	#	print("Successfully connected to database!")
	#except:
	#	print("Error connecting to mySQL database")
#
	#try:
	#	sql = "INSERT into alerts (datetimeinfo, alert) VALUES ('%s', 'Motion Captured')" % (datetime)
	#	print(sql)
	#	curs.execute(sql)
	#	db.commit()
	#	print("Successfully added into database")
	#except MySQLdb.Error as e:
	#	print e
	#except KeyboardInterrupt:
	#	update = False

#def store_temp_to_db(temperature):
#
	#try:
	#	db = MySQLdb.connect("localhost", "root", "dmitiot", "Assignment")
	#	curs = db.cursor()
	#except:
	#	print("Error connecting to mySQL database")
	#
	#try:
	#	sql = "INSERT into temp (temperature) VALUES ('%s')" % (temperature)
	#	curs.execute(sql)
	#	db.commit()
	#except MySQLdb.Error as e:
	#	print e
	#except KeyboardInterrupt:
	#	update = False

def connect_to_dynamodb_picuturesname():
	dynamodb = boto3.resource('dynamodb')
	table = dynamodb.Table('motionimage')
	data=[]
	response = table.query(
    KeyConditionExpression=Key('sensor').eq('motion')
	)
	items = response['Items']
	
	print(items)
	
	
	for item in items:
		timestamp = item['timestamp']
		data.append(timestamp)

	return data

#def alarmOn():
 #   	bz.off()
  #  	pir.wait_for_motion()
   # 	timestring = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
    #	print "Motion capture at: " + timestring
    #	bz.on()
    #	camera.capture('/home/pi/assignment/static/Capture/photo_'+timestring+'.jpg')
    #	bz.off()
    #	#store_alert_to_db(timestring)
    #	time.sleep(DELAY)

#def alarmOff():
	#pin = 4
	#humidity, temperature = Adafruit_DHT.read_retry(11, pin)
	#print('Temperature: {:.1f} C'.format(temperature)) 
	#print('Humidity: {:.1f}'.format(humidity))
	#current_temp = '{:.1f} C'.format(temperature)
	#store_temp_to_db(current_temp)
#	time.sleep(DELAY)

def led_status(value):
	GPIO.output(LED_PIN, value)

#Threading
#class alarm_system (threading.Thread):
#	def __init__(self):
#		threading.Thread.__init__(self)
#		self.alive = True
#		self.alarm = False
#
#	def run(self):
#		while self.alive:
#			if self.alarm:
#				alarmOn()
#			else:
#				alarmOff()

def getconnection():
		host = "a1ej0yhq6jfrhg.iot.us-west-2.amazonaws.com"
		rootCAPath = "VeriSign-Class 3-Public-Primary-Certification-Authority-G5.pem"
		certificatePath = "65d6589297-certificate.pem.crt"
		privateKeyPath = "65d6589297-private.pem.key"

		my_rpi = AWSIoTMQTTClient("subscriber")
		my_rpi.configureEndpoint(host, 8883)
		my_rpi.configureCredentials(rootCAPath, privateKeyPath, certificatePath)

		my_rpi.configureOfflinePublishQueueing(-1)  # Infinite offline Publish queueing
		my_rpi.configureDrainingFrequency(2)  # Draining: 2 Hz
		my_rpi.configureConnectDisconnectTimeout(10)  # 10 sec
		my_rpi.configureMQTTOperationTimeout(5)  # 5 sec

		return my_rpi

app = Flask(__name__)

@app.route("/")
def index():
 	return render_template('index.html')

@app.route("/led")
def led():
	
	return render_template('led.html')

@app.route("/temp")
def Temp():
	global globaltemp
	current_temp = " "
	current_humidity = " "
	print globaltemp
	global my_rpi
	my_rpi.subscribe("sensors/temperature", 1, customCallbackfortemperature)
	my_rpi.subscribe("sensors/humidity", 1, customCallbackforhumidity)
	if globaltemp is not None:
		current_temp = globaltemp['temperature']
	if globalhumidity is not None:
		current_humidity = globalhumidity['humidity']
	return render_template('temp.html', temp = current_temp,humidity = current_humidity)

@app.route("/ledlive")
def ledTemplive():
	global globaltemp
	current_temp = " "
	current_humidity = " "
	print globaltemp
	global my_rpi
	my_rpi.subscribe("sensors/temperature", 1, customCallbackfortemperature)
	
	if globaltemp is not None:
		current_temp = globaltemp['temperature']
	if globalhumidity is not None:
		current_humidity = globalhumidity['humidity']
	return jsonify(temp=current_temp,humidity=current_humidity)

@app.route("/alarm")
def captures():
	data=connect_to_dynamodb_picuturesname()
	return render_template('alarm.html', dates=data)

@app.route("/contactus")
def contactus():
	return render_template('contactus.html')


@app.route("/ledchange/<status>")
def writePin(status):
	global my_rpi
 	if status == 'On':
 		msg=json.dumps({"status":"On"})
		my_rpi.publish("sensors/lightmode",msg , 1)
 	else:
 		msg=json.dumps({"status":"Off"})
		my_rpi.publish("sensors/lightmode",msg , 1)

	

	return render_template('led.html')

@app.route("/alarmchange/<status>")
def writeAlarm(status):
	global my_rpi
	if status == 'On':
		msg=json.dumps({"status":"On"})
		my_rpi.publish("sensors/alarmmode",msg , 1)
		result = 'True'
	else:
		msg=json.dumps({"status":"Off"})
		my_rpi.publish("sensors/alarmmode",msg , 1)
		result = 'False'

	templateData = {
		'response' : result
	}

	return render_template('alarm.html', **templateData)


if __name__ == '__main__':

	my_rpi=getconnection()
	my_rpi.connect()
 	try:
 		http_server = WSGIServer(('0.0.0.0', 8001), app)
 		app.debug = True
 		http_server.serve_forever()
 	except:
 		print("Exception")