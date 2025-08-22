FROM python:3.10

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY messaging_app .

EXPOSE 8000

CMD ["python", "manage.py", "runserver", -p "0.0.0.0:8000"]

# FROM python:3.10-slim

# WORKDIR /app

# # Install system dependencies
# RUN apt-get update && apt-get install -y \
#     gcc \
#     default-libmysqlclient-dev \
#     pkg-config \
#     && rm -rf /var/lib/apt/lists/*

# # Copy requirements and install Python dependencies
# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

# # Copy project code
# COPY . .

# # Expose port
# EXPOSE 8000

# # Run application
# CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
