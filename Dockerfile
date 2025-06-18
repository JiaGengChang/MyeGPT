FROM python:3.12-slim

WORKDIR /app

COPY src .
COPY schema /schema
COPY refdata /ref
COPY requirements.txt .

RUN pip install -r requirements.txt
RUN pip install psycopg2-binary

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host=0.0.0.0", "--port=8080", "--reload"]