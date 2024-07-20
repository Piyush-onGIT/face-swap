FROM python:3.10-slim

RUN apt-get update && apt-get install -y     python3-tk     ffmpeg     libsm6     libxext6     libhdf5-dev     gcc     g++     make     libffi-dev     libssl-dev     python3-dev     pkg-config &&     rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/

RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

EXPOSE 5000

CMD [python, app.py]

