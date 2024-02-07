from celery import Celery
import os
from roop import core
import boto3
from dotenv import load_dotenv


load_dotenv()
# Create Celery instance
celery = Celery(__name__, broker='redis://localhost:6379/0', backend='redis://localhost:6379/0')

# Create an S3 client
s3 = boto3.client('s3', aws_access_key_id=os.environ.get('AWS_ACCESS_KEY'), aws_secret_access_key=os.environ.get('AWS_SECRET_KEY'), region_name='ap-south-1')

# os.environ['AWS_SHARED_CREDENTIALS_FILE'] = '/home/ubuntu/roop/aws-creds/credentials'

# Define Celery task
@celery.task
def process_images(source_image_path, target_image_path, output_image_path, output_filename):
  print("CELERY TASK RUNNING...")
  core.run(source_image_path, target_image_path, output_image_path)
  file_url = upload_image_to_s3(output_image_path, os.environ.get('AWS_BUCKET_NAME'), output_filename)
  return file_url


def upload_image_to_s3(file_path, bucket_name, object_name):
  try:
    print(f'Uploading {file_path}')
    s3.upload_file(file_path, bucket_name, object_name)
    file_url = f'https://{bucket_name}.s3.amazonaws.com/{object_name}'
    print("Upload Successful")
    return file_url
    # url_expires_in_seconds = 3600
    # presigned_url = s3.generate_presigned_url('get_object',
    #                                           Params={'Bucket': bucket_name, 'Key': 'object5_name.png'},
    #                                           ExpiresIn=url_expires_in_seconds)
    # print(presigned_url)
  except Exception as e:
    print(f"Upload Failed: {e}")