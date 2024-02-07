from celery import Celery
import os
from roop import core
import boto3
from dotenv import load_dotenv
from pymongo import MongoClient
import json

host = 'localhost'
port = 27017

client = MongoClient(host, port)
db = client['ai-photobooth']
collection = db['face-swaps']

load_dotenv()
# Create Celery instance
celery = Celery(__name__, broker='redis://localhost:6379/0', backend='redis://localhost:6379/0')

# Create an S3 client
s3 = boto3.client('s3', aws_access_key_id=os.environ.get('AWS_ACCESS_KEY'), aws_secret_access_key=os.environ.get('AWS_SECRET_KEY'), region_name='ap-south-1')

# os.environ['AWS_SHARED_CREDENTIALS_FILE'] = '/home/ubuntu/roop/aws-creds/credentials'

# Define Celery task
@celery.task
def process_images(source_image_path, target_image_path, output_image_path, output_filename):
  task_id = process_images.request.id
  print("CELERY TASK RUNNING...")
  print(f"Task id received: {task_id}")
  core.run(source_image_path, target_image_path, output_image_path)
  url = upload_image_to_s3(output_image_path, os.environ.get('AWS_BUCKET_NAME'), output_filename, task_id)
  return url


async def upload_image_to_s3(file_path, bucket_name, object_name, task_id):
  try:
    print(f'Uploading {file_path}')
    s3.upload_file(file_path, bucket_name, object_name, ExtraArgs={'ACL': 'public-read'})
    url = f"https://{os.environ.get('AWS_BUCKET_NAME')}.s3.amazonaws.com/{os.path.basename(object_name)}"
    print("Upload Successful")
    await websocket.send(json.dumps({'your-new-face': url}))
    saveToMongo(url, collection, task_id)
    return url
  except Exception as e:
    print(f"Upload Failed: {e}")

def saveToMongo(url, collection, task_id):
  collection.insert_one({"_id": task_id ,'image': url})

# @task_success.connect
# def handle_task_success():
