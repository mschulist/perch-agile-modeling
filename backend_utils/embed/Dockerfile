FROM --platform=amd64 tensorflow/tensorflow:2.17.0-gpu

COPY . /app

# Install dependencies
RUN apt-get update && apt-get install -y \
    git \
    wget \
    unzip \
    python3-pip

# Install python dependencies
RUN pip install --upgrade pip
RUN pip install -r /app/requirements.txt

# Run the application with parameters

ENTRYPOINT ["sh", "/app/run.sh"]