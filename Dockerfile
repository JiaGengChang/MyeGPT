FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/main.py .
COPY src/agent.py .
COPY src/tools.py .
COPY src/vectorstore.py .
COPY src/utils.py .
COPY src/models.py .
COPY src/mail.py .
COPY src/security.py .
COPY src/serialize.py .
COPY src/prompt.txt .
COPY src/static static
COPY src/templates templates
COPY refdata /refdata

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host=0.0.0.0", "--port=8080"]