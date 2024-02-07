from celery import Celery
import os
from roop import core
import boto3
from dotenv import load_dotenv


load_dotenv()

celery = Celery(__name__, broker='redis://redis:6379/0', backend='redis://redis:6379/0')

s3 = boto3.client('s3', aws_access_key_id=os.environ.get('AWS_ACCESS_KEY'), aws_secret_access_key=os.environ.get('AWS_SECRET_KEY'), region_name='ap-south-1')

# Define Celery task
@celery.task
def process_images(source_image_path, target_image_path, output_image_path, output_filename):
  print("CELERY TASK RUNNING...")
  core.run(source_image_path, target_image_path, output_image_path)
  url = upload_image_to_s3(output_image_path, os.environ.get('AWS_BUCKET_NAME'), output_filename)
  return url

def upload_image_to_s3(file_path, bucket_name, object_name):
  try:
    s3.upload_file(file_path, bucket_name, object_name, ExtraArgs={'ACL': 'public-read'})
    url = f"https://{os.environ.get('AWS_BUCKET_NAME')}.s3.amazonaws.com/{os.path.basename(object_name)}"
    return url
  except Exception as e:
    print(f"Upload Failed: {e}")