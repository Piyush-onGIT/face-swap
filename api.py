import os
import uuid
from flask import Flask, jsonify, request
from werkzeug.utils import secure_filename
from tasks import process_images
import boto3
from pymongo import MongoClient
from datetime import timedelta
from flask_cors import CORS
import redis
import requests
import base64
import aiohttp
import asyncio
import redis

app = Flask(__name__)

allowed_origins = [
    'http://localhost:3000',
    'http://127.0.0.1:5500',
    'https://roop.gokapturehub.com',
    'http://localhost:5173'
]
# CORS(app, origins=allowed_origins)
CORS(app)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

host = 'mongodb'
port = 27017

client = MongoClient(host, port)
db = client['ai-photobooth']
collection = db['face-swaps']


# Check if the uploaded file has a valid extension


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Generate a unique filename


def generate_unique_filename():
    return str(uuid.uuid4())


# Endpoint to receive and process images
@app.route('/process_image', methods=['POST'])
def process_images_route():
  if 'source_image' not in request.files or 'target_image' not in request.files:
    return jsonify({"error": "Source or target image not provided"}), 400

  source_image = request.files['source_image']
  target_image = request.files['target_image']

  # Save the uploaded images
  source_filename = generate_unique_filename() + '.' + source_image.filename.rsplit('.', 1)[1].lower()
  target_filename = generate_unique_filename() + '.' + target_image.filename.rsplit('.', 1)[1].lower()
  output_filename = generate_unique_filename() + '.jpg'

  source_image_path = os.path.join(app.config['UPLOAD_FOLDER'], source_filename)
  target_image_path = os.path.join(app.config['UPLOAD_FOLDER'], target_filename)
  output_image_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)

  source_image.save(source_image_path)
  target_image.save(target_image_path)

  # Queue the task to process the images
  result = process_images.delay(source_image_path, target_image_path, output_image_path, output_filename)
  return jsonify({"task_id": result.id}), 202


@app.route('/check/<task_id>', methods=['GET'])
def get_task_time_left(task_id):
  result = process_images.AsyncResult(task_id)

  if result.state == 'PENDING':
    return jsonify({"message": "Task is still pending"}), 200
  elif result.state == 'SUCCESS':
    timestamp = result.date_done
    time_delta = timedelta(hours=5, minutes=30)
    timestamp = timestamp + time_delta
    return jsonify({"message": "Task has already completed", "result": result.result, "finished_at": timestamp}), 200

  eta = result.eta
  if eta:
    time_left = eta - datetime.utcnow()
    time_left_seconds = max(time_left.total_seconds(), 0)
  else:
    time_left_seconds = None

  return jsonify({"task_id": task_id, "time_left_seconds": time_left_seconds}), 200


@app.route('/send_whatsapp_message', methods=['POST'])
def send_whatsapp_message():
  data = request.json
  taskId = data.get('taskId', None)
  phone = data.get('phone', None)

  if not taskId:
    return jsonify({"message": "Invalid taskId"})
  
  if not phone:
    return jsonify({"message": "Invalid phone number"})

  phone = "91" + phone

  while process_images.AsyncResult(taskId).state == 'PENDING':
    pass

  imageUrl = process_images.AsyncResult(taskId).result
  resultBase64 = url_to_base64(imageUrl)
  
  api_url = 'http://whatsapp_api:3000/api/sendImage'
  data = {'chatId': f'{phone}@c.us', 'file': {"mimetype": "image/jpeg", "filename": "aiimage.jpg", "data": resultBase64}, "caption": "GeM crossed the ₹3 Lakh Crore\nmilestone today! As a member of\nthe GeM family, I am honoured to\nbe a\npart of this incredible journey\ntowards transforming procurement\nin India.\nI am proud to be a part of\n#TeamGeM\n#GeMIndia #3LakhCroreGMV\n#GeM_Unstoppable\n#TeamGeMRocks", "session": "default"}

  loop = asyncio.new_event_loop()
  asyncio.set_event_loop(loop)
  result = loop.run_until_complete(call_third_party_api(api_url, data))

  return jsonify({"message": 'Sent'})


@app.route('/', methods=['GET'])
def test():
  return 'OK'


@app.route('/getImages', methods=['GET'])
def getImages():
  images = list(collection.find())
  return jsonify(images)


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


async def call_third_party_api(url, data):
  async with aiohttp.ClientSession() as session:
    async with session.post(url, json=data) as response:
      return await response.text()


if __name__ == "__main__":
  # app.run(app, debug=True)
  app.run(host='0.0.0.0', port=5000, debug=True)