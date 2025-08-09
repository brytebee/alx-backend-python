FROM python:3.10

WORKDIR /app

COPY requirement.txt .

RUN pip install -r requirement.txt

COPY messaging_app .

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
