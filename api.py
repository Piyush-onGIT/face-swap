import os
import uuid
from flask import Flask, jsonify, request
from werkzeug.utils import secure_filename
from tasks import process_images
import boto3

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

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
  output_image_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename,)

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
    return jsonify({"message": "Task has already completed", "result": result.result, "finished_at": result.date_done}), 200

  eta = result.eta
  if eta:
    time_left = eta - datetime.utcnow()
    time_left_seconds = max(time_left.total_seconds(), 0)
  else:
    time_left_seconds = None

  return jsonify({"task_id": task_id, "time_left_seconds": time_left_seconds}), 200


@app.route('/', methods=['GET'])
def test():
  return 'OK'

if __name__ == '__main__':
    app.run(debug=True)
