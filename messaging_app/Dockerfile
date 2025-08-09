from python:3.10

WORKDIR /app

COPY requirement.txt .

RUN pip install -r requirement.txt

COPY messaging_app .

CMD ["python", "manage.py", "runserver"]