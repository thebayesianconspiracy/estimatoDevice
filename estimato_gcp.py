
from picamera import PiCamera
import io
import google.auth
from google.cloud import vision
from fuzzywuzzy import process
from fuzzywuzzy import fuzz
import time


camera = PiCamera()
list_of_vegetables = ["onion", "tomato", "bell pepper", "cucumber", "lemon"]
FUZZY_THRESHOLD = 60

def findMostProbableVegetable(labels):
    for label in labels:
        print label.description," ",label.score
        extractedVegetable = process.extractOne(label.description, list_of_vegetables, scorer=fuzz.token_sort_ratio)
        if (extractedVegetable[1] > FUZZY_THRESHOLD):
            return extractedVegetable[0]
    return "None"
        

credentials, project = google.auth.default()

"""Detects labels in the file."""
vision_client = vision.Client(credentials=credentials)

name = str(time.time()).split('.')[0]
image_path = './image_' + name + '.jpg'
camera.capture(image_path)

with io.open(image_path, 'rb') as image_file:
    content = image_file.read()
    image = vision_client.image(content=content)

    labels = image.detect_labels()

    print str(findMostProbableVegetable(labels))
                                
