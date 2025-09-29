FROM python:3.13-slim

WORKDIR /app

COPY src/main.py .
COPY src/agent.py .
COPY src/tools.py .
COPY src/vectorstore.py .
COPY src/utils.py .
COPY src/prompt.txt .
COPY src/static static
COPY refdata /refdata
COPY requirements.txt .

RUN pip install -r requirements.txt

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host=0.0.0.0", "--port=8080"]