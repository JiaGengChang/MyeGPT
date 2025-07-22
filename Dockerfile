FROM python:3.12-slim

WORKDIR /app

COPY src/main.py .
COPY src/agent.py .
COPY src/dbdesc.py .
COPY src/prompt.py .
COPY src/static static
COPY schema /schema
COPY refdata /refdata
COPY requirements.txt .

RUN pip install -r requirements.txt

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host=0.0.0.0", "--port=8080"]