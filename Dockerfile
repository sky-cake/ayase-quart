# Use the official Fedora image
FROM fedora:latest

# Set the working directory
WORKDIR /app

# Install necessary system dependencies
RUN dnf install -y \
    python3.12 \
    python3.12-pip \
    python3-virtualenv \
    python3-devel \
    mysql-devel \
    gcc \
    && dnf clean all
    
# Create a virtual environment and install dependencies
COPY requirements.txt /app/
RUN python3.12 -m venv /app/venv
RUN /app/venv/bin/pip install -r /app/requirements.txt

# Copy the source files to the container
COPY src/ /app/src/

# Create secret.txt with random text
RUN tr -dc A-Za-z0-9 </dev/urandom | head -c 64 > /app/src/secret.txt

# Copy SSL certificates (assumed to be in the same directory as Dockerfile)
COPY cert.pem /app/src/
COPY key.pem /app/src/

# Expose the necessary port
EXPOSE 9001

# Run the web server
# https://hypercorn.readthedocs.io/en/latest/how_to_guides/configuring.html#configuration-options
CMD ["/app/venv/bin/hypercorn", "-w", "2", "-b", "0.0.0.0:9001", "--certfile", "src/cert.pem", "--keyfile", "src/key.pem", "src/main:app"]

# Visit AQ in your browser: https://IP:9001
# Get the IP with: sudo docker inspect $(sudo docker compose ps -q ayase_quart) | grep IPAddress