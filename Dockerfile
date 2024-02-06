FROM python:3.10

WORKDIR /app

Run apt-get update
Run apt-get install python3-tk -y
Run apt-get install ffmpeg libsm6 libxext6 -y

# Install Python dependencies
COPY requirements.txt /app/
COPY requirements-headless.txt /app/
RUN pip install -r requirements.txt
RUN pip install -r requirements-headless.txt

COPY . /app/

EXPOSE 5000

CMD ["gunicorn", "-b", "0.0.0.0:5000", "api:app"]
