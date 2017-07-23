from google.cloud import vision
from fuzzywuzzy import process
from fuzzywuzzy import fuzz
from picamera import PiCamera
from hx711 import HX711
import RPi.GPIO as GPIO
import time, json, sys, math, io
import paho.mqtt.client as paho
import google.auth

class Payload:
    deviceID = ""
    appID = ""
    weight = 0
    label = ""
    def __init__(self, deviceID, appID):
        self.deviceID = deviceID
        self.appID = appID
    def setWeight(self,weight):
        self.weight = weight
    def setLabel(self,label):
        self.label = label

def isAllEqual(weightBuffer):
	average = sum(weightBuffer)/len(weightBuffer)
	for weight in weightBuffer:
		if (math.fabs(weight - average) > 0.05 * average and math.fabs(weight - average) > 5):
			return 0 
	return 1

def findMostProbableVegetable(labels):
    for label in labels:
        #print label.description," ",label.score
        extractedVegetable = process.extractOne(label.description, list_of_vegetables, scorer=fuzz.token_sort_ratio)
        if (extractedVegetable[1] > FUZZY_THRESHOLD):
            return extractedVegetable[0]
    return "None"

def on_connect(client, userdata, rc):
    print("Connected with result code "+str(rc))
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("$SYS/#")

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
    #print(msg.payload) 

def getLabel(image_path):
    with io.open(image_path, 'rb') as image_file:
        content = image_file.read()
    image = vision_client.image(content=content)
    labels = image.detect_labels()
    return findMostProbableVegetable(labels)

def setupMQTT():
    client.on_publish = on_publish
    client.on_connect = on_connect
    client.on_subscribe = on_subscribe
    client.on_message = on_message
    client.connect(broker, 1883)
    client.loop_start()

def setupGCP():
   credentials, project = google.auth.default()
   vision_client = vision.Client(credentials=credentials)

def setupHX711():
   hx = HX711(23, 24)
   hx.set_reading_format("LSB", "MSB")
   hx.set_reference_unit(92)
   hx.reset()
   hx.tare()

def setup():
   GPIO.setup(4, GPIO.OUT)
   setupMQTT()
   setupGCP()
   setupHX711()
 
def run():
    ## MQTT
    packet = Payload(deviceID,appID)
    topic = "estimato/" + deviceID + "/item"
    ## Weight Stabilisation
    weightBuffer = [0] * 10
    oldWeight = 0
    newWeight = 0
    weightChangeThreshold = 10
    ## Runner
    while True:
        print "Loop Started"
        val = -1 * hx.get_weight(5)
        print "Sensor reading : " + str(val)
        hx.power_down()
        hx.power_up()
	weightBuffer.append(val)
	weightBuffer.pop(0)
	print weightBuffer

	if (allEqual(weightBuffer) == 0):
		print "Weight unstable" 
		GPIO.output(4, GPIO.LOW)
		client.publish(topic, "wait", qos=0)
	elif (allEqual(weightBuffer) != 0):
		print "Weight stable. Current Weight : " + str(oldWeight) 
		weightChange = math.fabs(val - oldWeight)
		print "weight change " + str(weightChange)
		client.publish(topic, "ready", qos=0)
		if (weightChange > weightChangeThreshold):
			print "Weight change more than threshold"
			if (val > oldWeight):
				print "Weight increased"
				name = str(time.time()).split('.')[0]
                                image_path = '/home/pi/Desktop/estimatoDevice/images/image_' + name + '.jpg'
				camera.capture(image_path)
                                label = getLabel(image_path)
				print label
				oldWeight = val
				packet.setWeight(val)
				packet.setLabel(label)
				client.publish(topic, json.dumps(packet.__dict__), qos=0)
			else:
				print "Weight decreased"
				hx.tare()
				oldWeight = 0
		GPIO.output(4, GPIO.HIGH)
	else:
		GPIO.output(4, GPIO.LOW)
        time.sleep(0.1)
        
def main():
    list_of_vegetables = ["onion", "tomato", "sk "]
    FUZZY_THRESHOLD = 60
    deviceID = "ESTIMATO__001"
    appID = "APP_01"
    broker = sys.argv[1]
    try:
        camera = PiCamera()
        setup()
        run()
    except (KeyboardInterrupt, SystemExit):
        cleanAndExit()

if __name__ == "__main__":
    main()
