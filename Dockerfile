FROM python:3.10

WORKDIR /app

RUN apt-get update
RUN apt-get install python3-tk -y
RUN apt-get install ffmpeg libsm6 libxext6 -y

# Install Python dependencies
COPY requirements.txt /app/
COPY requirements-headless.txt /app/
RUN pip install -r requirements.txt
RUN pip install -r requirements-headless.txt
#RUN pip install --upgrade --force-reinstall keras
#RUN pip install --upgrade tensorflow

COPY . /app/

EXPOSE 5000
