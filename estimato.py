
from google.cloud import vision
from fuzzywuzzy import process
from fuzzywuzzy import fuzz
from picamera import PiCamera
from hx711 import HX711
import RPi.GPIO as GPIO
import time, json, sys, math, io
import paho.mqtt.client as paho
import google.auth

list_of_vegetables = ["onion", "tomato", "sk "]
FUZZY_THRESHOLD = 60

def findMostProbableVegetable(labels):
    for label in labels:
        print label.description," ",label.score
        extractedVegetable = process.extractOne(label.description, list_of_vegetables, scorer=fuzz.token_sort_ratio)
        if (extractedVegetable[1] > FUZZY_THRESHOLD):
            return extractedVegetable[0]
    return "None"


deviceID = "CART__0_40"
appID = "CART_0"
#DOUT, SCK
hx = HX711(23, 24)
#broker = sys.argv[1]
topic = "quine/" + deviceID + "/weight"
action_topic = "quine/" + deviceID + "/action"
status_topic = "quine/" + deviceID + "/appStatus"
last_will_topic = "quine/" + deviceID + "/deviceStatus"
last_will_message = "offline"
GPIO.setup(4, GPIO.OUT)
camera = PiCamera()

def on_connect(client, userdata, rc):
    print("Connected with result code "+str(rc))
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("$SYS/#")
    client.subscribe(action_topic, qos=0)
    client.subscribe(status_topic, qos=0)

def on_publish(client, userdata, mid):
    print("published : "+str(mid))
 
def cleanAndExit():
    print "Cleaning..."
    GPIO.cleanup()
    client.loop_stop()
    client.disconnect()
    print "Bye!"
    sys.exit()

def on_subscribe(client, userdata, mid, granted_qos):
    print("Subscribed: "+str(mid)+" "+str(granted_qos))
 
def on_message(client, userdata, msg):
    jsonMsg = json.loads(str(msg.payload))
    global deviceInfo
    if(msg.topic == action_topic):
    	if(jsonMsg['tare']==1):
	    hx.tare()
	    print("Tare")
    if(msg.topic == status_topic):
        deviceInfo.updateInfo(jsonMsg['cartComputedWeight'], jsonMsg['weightConvFactor'], jsonMsg['weightChangeThreshold'])	
    #print(msg.payload) 

class Payload:
    deviceID = ""
    appID = ""
    weight = 0
    def __init__(self, deviceID, appID):
        self.deviceID = deviceID
        self.appID = appID
    def setWeight(self,weight):
        self.weight = weight

def allEqual(weightBuffer):
	average = sum(weightBuffer)/len(weightBuffer)
	for weight in weightBuffer:
		if (math.fabs(weight - average) > 0.05 * average and math.fabs(weight - average) > 5):
			return 0 
	return 1
    
client = paho.Client(client_id="pi_device_1")
client.on_publish = on_publish
client.on_connect = on_connect
client.on_subscribe = on_subscribe
client.on_message = on_message

packet = Payload(deviceID,appID)
client.will_set(last_will_topic, last_will_message, 0, False)

#client.connect(broker, 1883)
#client.loop_start()
hx.set_reading_format("LSB", "MSB")
hx.set_reference_unit(92)

hx.reset()
hx.tare()

credentials, project = google.auth.default()

"""Detects labels in the file."""
vision_client = vision.Client(credentials=credentials)


weightBuffer = [0] * 10
oldWeight = 0
newWeight = 0
weightChangeThreshold = 10

def getLabel(image_path):
    with io.open(image_path, 'rb') as image_file:
        content = image_file.read()
    image = vision_client.image(content=content)
    labels = image.detect_labels()
    return findMostProbableVegetable(labels)


while True:
    try:
        val = -1 * hx.get_weight(5)
        print "Sensor reading : " + str(val)
        hx.power_down()
        hx.power_up()
	weightBuffer.append(val)
	weightBuffer.pop(0)
	print weightBuffer

        packet.setWeight(val)
        #client.publish(topic, json.dumps(packet.__dict__), qos=0)
	if (allEqual(weightBuffer) == 0):
		print "Weight unstable" 
		GPIO.output(4, GPIO.LOW)
	elif (allEqual(weightBuffer) != 0):
		print "Weight stable. Current Weight : " + str(oldWeight) 
		weightChange = math.fabs(val - oldWeight)
		print "weight change " + str(weightChange)
		if (weightChange > weightChangeThreshold):
			print "Weight change more than threshold"
			if (val > oldWeight):
				print "Weight increased"
				name = str(time.time()).split('.')[0]
                                image_path = '/home/pi/Desktop/estimatoDevice/images/image_' + name + '.jpg'
				camera.capture(image_path)
                                print getLabel(image_path)
                                
				oldWeight = val
			else:
				print "Weight decreased"
				oldWeight = val
		GPIO.output(4, GPIO.HIGH)
	else:
		GPIO.output(4, GPIO.LOW)
        time.sleep(0.1)
    except (KeyboardInterrupt, SystemExit):
        cleanAndExit()
