from celery import Celery
import os
from roop import core

# Create Celery instance
celery = Celery(__name__, broker='redis://localhost:6379/0')

# Define Celery task
@celery.task
def process_images(source_image_path, target_image_path, output_image_path):
  print("CELERY TASK RUNNING...")
  # output_path = os.path.join('uploads', 'output.jpg')
  # command = f"python run.py -s {source_image_path} -t {target_image_path} -o {output_image_path} --frame-processor face_swapper face_enhancer"
  # os.system(command)
  core.run(source_image_path, target_image_path, output_image_path)
  return output_image_path
