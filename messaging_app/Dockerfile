FROM python:3.10

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY messaging_app .

CMD ["python", "manage.py", "runserver", -p "0.0.0.0:8000"]
