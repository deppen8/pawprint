FROM python:3.7.5-buster

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install requirements first so env will cache if unchanged
COPY requirements_dev.txt /pawprint/

# Install required packages
RUN pip install --no-cache-dir -r /pawprint/requirements_dev.txt

#Create a non-root user and set a working folder
# RUN useradd --create-home pawprint_dev
# USER pawprint_dev
# WORKDIR /home/pawprint_dev

# WORKDIR /pawprint

# Create the rest of the files
COPY . /pawprint
WORKDIR /pawprint

# Install package in developer mode
RUN pip install -e .
