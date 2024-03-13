from celery import Celery
import os
from roop import core
import boto3
from dotenv import load_dotenv
from pymongo import MongoClient
import redis
import base64
import requests
from datetime import datetime
from bson import ObjectId

load_dotenv()

host = os.environ.get('MONGODB_URL')
port = int(os.environ.get('MONGODB_PORT'))

client = MongoClient(host, port)
db = client[os.environ.get('MONGO_DB_NAME')]
collection = db['aiphotobooths']

redis_host = os.environ.get('REDIS_HOST')
redis_port = int(os.environ.get('REDIS_PORT'))


# Create Celery instance
celery = Celery(__name__, broker=f'redis://{redis_host}:{redis_port}/0', backend=f'redis://{redis_host}:{redis_port}/0')
redis_client = redis.Redis(host=redis_host, port=redis_port, db=0)

# Create an S3 client
s3 = boto3.client('s3', aws_access_key_id=os.environ.get('AWS_ACCESS_KEY'), aws_secret_access_key=os.environ.get('AWS_SECRET_KEY'), region_name='ap-south-1')


def url_to_base64(image_url):
  try:
    response = requests.get(image_url)
    if response.status_code == 200:
      image_base64 = base64.b64encode(response.content).decode('utf-8')
      return image_base64
    else:
      return None
  except Exception as e:
    return None


# Define Celery task
@celery.task
def process_images(source_image_path, target_image_path, output_image_path, output_filename, event_id, frame_url):
  task_id = process_images.request.id
  print("CELERY TASK RUNNING...")
  print(f"Task id received: {task_id}")
  core.run(source_image_path, target_image_path, output_image_path)
  url = upload_image_to_s3(output_image_path, task_id, event_id, frame_url)
  redis_client.publish('task_completed', f"{event_id}:{url}")
  redis_client.publish('task_completed', f"{task_id}:{url}")

  if os.path.exists(source_image_path):
    os.remove(source_image_path)
  if os.path.exists(target_image_path):
    os.remove(target_image_path)
  if os.path.exists(output_image_path):
    os.remove(output_image_path)
  
  print("URL for the image: ", url)
  return url


def upload_image_to_s3(file_path, task_id, event_id, frame_url):
  try:
    # print(f'Uploading {file_path}')
    # s3.upload_file(file_path, bucket_name, object_name, ExtraArgs={'ACL': 'public-read'})
    # url = f"https://{os.environ.get('AWS_BUCKET_NAME')}.s3.amazonaws.com/{os.path.basename(object_name)}"
    # print("Upload Successful")
    
    overlay_base64 = ''
    if frame_url:
      overlay_base64 = url_to_base64(frame_url)
      # print('frame', 'overlay_base64')  
    else:
      overlay_base64 = None
      # with open('frame.png', 'rb') as data:
      #   overlay_data = data.read()
      #   overlay_base64 = base64.b64encode(overlay_data).decode('utf-8')
      #   print('frameless', 'overlay_base64')

    with open(file_path, 'rb') as data:
      file_data = data.read()
      file_base64 = base64.b64encode(file_data).decode('utf-8')
      payload = {
          'base': file_base64,
          # path frame.png as base64
          'overlay': overlay_base64,
          'uploadFor': os.environ.get('AWS_S3_FOLDER_NAME')
      }
      response = requests.post("https://s39nhbwtx9.execute-api.ap-south-1.amazonaws.com/template", json=payload)
      print(response)
      url = response.json().get('image')
      saveToMongo(url, collection, task_id, event_id)
      return url
  except Exception as e:
    print(f"Upload Failed: {e}")


def saveToMongo(url, collection, task_id, event_id):
  timestamp = datetime.now()
  result = collection.update_one(
    {"_id": ObjectId(event_id)},
    {"$push": {"data": {"imageLink": url, "timestamp": timestamp}}}
  )
  # collection.insert_one({"_id": task_id ,'image': url})