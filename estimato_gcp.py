import io
import google.auth
from google.cloud import vision
from fuzzywuzzy import process
from fuzzywuzzy import fuzz


list_of_vegetables = ["onion", "tomato", "sk "]

def findMostProbableVegetable(labels):
    for label in labels:
        return process.extractOne(label.description, list_of_vegetables, scorer=fuzz.token_sort_ratio)[0]
        

credentials, project = google.auth.default()

"""Detects labels in the file."""
vision_client = vision.Client(credentials=credentials)

image_path='/home/pi/Desktop/image.jpg'

with io.open(image_path, 'rb') as image_file:
    content = image_file.read()
    image = vision_client.image(content=content)

    labels = image.detect_labels()

    print findMostProbableVegetable(labels)
                                
