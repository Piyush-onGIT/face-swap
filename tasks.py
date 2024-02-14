from celery import Celery
import os
from roop import core
import boto3
from dotenv import load_dotenv
from pymongo import MongoClient
import redis
import base64
import requests

host = 'mongodb'
port = 27017

client = MongoClient(host, port)
db = client['ai-photobooth']
collection = db['face-swaps']

load_dotenv()

# Create Celery instance
celery = Celery(__name__, broker='redis://redis:6379/0', backend='redis://redis:6379/0')
redis_client = redis.Redis(host='redis', port=6379, db=0)

# Create an S3 client
s3 = boto3.client('s3', aws_access_key_id=os.environ.get('AWS_ACCESS_KEY'), aws_secret_access_key=os.environ.get('AWS_SECRET_KEY'), region_name='ap-south-1')


# Define Celery task
@celery.task
def process_images(source_image_path, target_image_path, output_image_path, output_filename):
  task_id = process_images.request.id
  print("CELERY TASK RUNNING...")
  print(f"Task id received: {task_id}")
  core.run(source_image_path, target_image_path, output_image_path)
  url = upload_image_to_s3(output_image_path, task_id)
  redis_client.publish('task_completed', f"{task_id}:{url}")
  print("URL for the image: ", url)
  return url


def upload_image_to_s3_old(file_path, bucket_name, object_name, task_id):
  try:
    print(f'Uploading {file_path}')
    s3.upload_file(file_path, bucket_name, object_name)
    url = f"https://{os.environ.get('AWS_BUCKET_NAME')}.s3.amazonaws.com/{os.path.basename(object_name)}"
    print("Upload Successful")
    saveToMongo(url, collection, task_id)
    return url
  except Exception as e:
    print(f"Upload Failed: {e}")


def upload_image_to_s3(file_path, task_id):
  try:
    # print(f'Uploading {file_path}')
    # s3.upload_file(file_path, bucket_name, object_name, ExtraArgs={'ACL': 'public-read'})
    # url = f"https://{os.environ.get('AWS_BUCKET_NAME')}.s3.amazonaws.com/{os.path.basename(object_name)}"
    # print("Upload Successful")
    with open('frame.png', 'rb') as data:
      overlay_data = data.read()
      overlay_base64 = base64.b64encode(overlay_data).decode('utf-8')

    with open(file_path, 'rb') as data:
      file_data = data.read()
      file_base64 = base64.b64encode(file_data).decode('utf-8')
      payload = {
          'base': file_base64,
          # path frame.png as base64
          'overlay': overlay_base64, 
          'uploadFor':'aibooth-12thfeb'
      }
      response = requests.post("https://s39nhbwtx9.execute-api.ap-south-1.amazonaws.com/template", json=payload)
      print(response)
      url = response.json().get('image')
      saveToMongo(url, collection, task_id)
      return url
  except Exception as e:
    print(f"Upload Failed: {e}")


def saveToMongo(url, collection, task_id):
  collection.insert_one({"_id": task_id ,'image': url})