FROM python:3.12

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["gunicorn", "digiauto_api.wsgi:application", "--bind", "0.0.0.0:8000"]