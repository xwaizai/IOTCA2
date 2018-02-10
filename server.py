# Import SDK packages
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
from time import sleep
from gpiozero import LED, MotionSensor, Buzzer, MCP3008
from picamera import PiCamera

import RPi.GPIO as GPIO
import json
import Adafruit_DHT
import threading
import boto3
import botocore
import time

globalalarm = None
bz = Buzzer(5)
pir = MotionSensor(26, sample_rate=5,queue_len=1)
camera = PiCamera()
LED_PIN = 18
GPIO.setmode(GPIO.BCM)
GPIO.setup(18, GPIO.OUT)
s3 = boto3.resource('s3')

def led_status(value):
    GPIO.output(18, value)

def customCallbacklight(client, userdata, message):
    global globallight
    print("Received a new message: ")
    print(message.payload)
    print("from topic: ")
    print(message.topic)
    globallight = json.loads(message.payload)
    if globallight['status'] == 'On':
        response = led_status(True)
        result = 'True'
    else:
        response = led_status(False)
        result = 'False'
    print("--------------\n\n")

def temp_humid(timestamp):	
	pin = 4
	humidity, temperature = Adafruit_DHT.read_retry(11, pin)
	print('Temperature: {:.1f} C'.format(temperature))
	print('Humidity: {:.1f}'.format(humidity))
	current_temp = '{:.1f}C'.format(temperature)
	current_humid = '{:.1f}%'.format(humidity)
	msg=json.dumps({"timestamp":timestamp,"temperature":current_temp,"humidity":current_humid})
	return msg

def uploadpicture(full_path, timestring):
	bucket_name = 'jcimagebucket' # replace with your own unique bucket name
	exists = True
	try:
    		s3.meta.client.head_bucket(Bucket=bucket_name)
	except botocore.exceptions.ClientError as e:
    		error_code = int(e.response['Error']['Code'])
		if error_code == 404:
        		exists = False

	if exists == False:
  		s3.create_bucket(Bucket=bucket_name,CreateBucketConfiguration={'LocationConstraint': 'us-west-2'})
	s3.Object(bucket_name, timestring+".jpg").put(Body=open(full_path, 'rb'))
	print("File uploaded")

#s3.upload_file(full_path, bucket_name, file_name)

# Custom MQTT message callback
def customCallback(client, userdata, message):
	global globalalarm
	print("Received a new message: ")
	print(message.payload)
	print("from topic: ")
	print(message.topic)
	globalalarm = json.loads(message.payload)
	print globalalarm['status']
	if globalalarm['status'] == 'On':
		print("Alarm is On")
		alarmsys.alarm = True
		print("Dicks")
		result = 'True'
	else:
		alarmsys.alarm = False
		result = 'False'
	print("--------------\n\n")
	


# Publish to the same topic in a loop forever

def alarmOn():
    print("Motion Captured")
    bz.off()
    pir.wait_for_motion()
    print("Motion Captured")
    timestring = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
    print "Motion capture at: " + timestring
    bz.on()
    full_path='/home/pi/assignment/static/Capture/photo_'+timestring+'.jpg'
    camera.capture(full_path)
    bz.off()
    uploadpicture(full_path, timestring)
    msg=json.dumps({"sensor":"motion","timestamp":timestring})
    my_rpi.publish("sensors/motion",msg , 1)
    sleep(5)

def alarmOff():
	timestring = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
	msg=temp_humid(timestring)
    	my_rpi.publish("sensors/all", msg, 1)
	sleep(5)

class alarm_system (threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self)
		self.alive = True
		self.alarm = False

	def run(self):
		while self.alive:
			if self.alarm:
				alarmOn()
			else:
				alarmOff()

host = "a1ej0yhq6jfrhg.iot.us-west-2.amazonaws.com"
rootCAPath = "VeriSign-Class 3-Public-Primary-Certification-Authority-G5.pem"
certificatePath = "65d6589297-certificate.pem.crt"
privateKeyPath = "65d6589297-private.pem.key"

my_rpi = AWSIoTMQTTClient("publisher")
my_rpi.configureEndpoint(host, 8883)
my_rpi.configureCredentials(rootCAPath, privateKeyPath, certificatePath)

my_rpi.configureOfflinePublishQueueing(-1)  # Infinite offline Publish queueing
my_rpi.configureDrainingFrequency(2)  # Draining: 2 Hz
my_rpi.configureConnectDisconnectTimeout(10)  # 10 sec
my_rpi.configureMQTTOperationTimeout(5)  # 5 sec

# Connect and subscribe to AWS IoT
my_rpi.connect()
my_rpi.subscribe("sensors/alarmmode", 1, customCallback)
my_rpi.subscribe("sensors/lightmode", 1, customCallbacklight)

sleep(2)
alarmsys = alarm_system()
alarmsys.start()