FROM --platform=amd64 python:3.11-slim

COPY . /app

WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y \
    git \
    wget \
    unzip \
    python3-pip

# Install python dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Run the application with parameters

ENTRYPOINT ["sh", "run.sh"]