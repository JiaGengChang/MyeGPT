# MyeGPT

An agentic conversation application for researchers to mine the MMRF-CoMMpass dataset, built with LangChain.

Designed towards smartphone browsers, it aims to accelerate hypothesis generation among wet-lab researchers by giving access to clinical cohort data at their fingertips.

<img height="800" width="536" alt="Phone site demonstration screenshot" src="https://github.com/user-attachments/assets/8ecc60f5-4d9d-4f6e-8685-0f9b557500be" />


# Use cases

1. Gene expression clustering

https://github.com/user-attachments/assets/dd7e1d1e-6ef0-4d8e-89e7-4b2fe5948437

2. Gene expression heatmap

https://github.com/user-attachments/assets/9d4fe841-4e9c-4a08-bfd0-cd8828802f90

3. CoxPH survival regression

https://github.com/user-attachments/assets/e24218f9-fc98-43c7-bd72-a54626944fd5

# Example from login page

https://github.com/user-attachments/assets/97444fee-7873-46c9-b781-b1641bcfdd17


# Pre-requisites
1. Docker desktop

1. Create a python 3.13 virtual environment

2. Install requirements.txt e.g., `pip install -r requirements.txt`

## Step 1. Database

1. Create a PostgreSQL 18 instance with the PgVector extension installed. Suggested docker image: `pgvector/pgvector:pg18-trixie`

2. Download CoMMpass files and place them into `omicdata` and `clindata`. These flatfiles will be used to build the database.

3. Set the `DBHOSTNAME`, `DBUSERNAME`, and `DBPASSWORD` environment variables

4. Inside pgsql, create a database named `commpass` and 3 schemas: `auth`, `document_embeddings`, and `checkpoints`.

3. Populate the `commpass.public` schema. This will upload CoMMpass data from the flatfiles:

    `cd [MYEGPT-HOME-DIRECTORY]`

    `python create_database.py`

    This script takes roughly 20 minutes

4. Populate the `commpass.document_embeddings` schema. This will upload the usage guides in `/docs` folder:

    `python create_vectorstore.py`

## Step 2. Acquire Mail server

1. Create an email server which the application can use to send emails with. 

    This is needed for email verification as part of account registration. 

2. Set the following environment variables
    ```
    MAIL_USERNAME=[admin@your-domain.com]
    MAIL_PASSWORD=[your-mail-server-password]
    MAIL_SERVER=[smtp.your-mail-service-provider.com]
    ```

## Step 3. API keys

1. Create and fund a developer account with the following supported LLM providers

    1. OpenAI

    2. Anthropic Claude

    3. Google Gemini AI

    4. AWS (need to enable the Bedrock service)

2. Create a developer account with following text embedding service providers

    1. OpenAI

    2. MistralAI

    3. AWS (need to enable the Bedrock service)

    4. Google Gemini AI

3. For path of least resistance, opt for OpenAI for both LLM and text embedding.

4. Set the environment variables. e.g., OPENAI_API_KEY, MISTRAL_API_KEY, etc

## Step 4. Build and deploy

1. Build the application

    `docker build -t [your-container-name]:[your-tag-name]` 

    Example `docker build -t myegpt:latest`.

2. Populate `.env` file with your API keys/secrets. Refer to `src/example.env`.

3. Launch the application

    `cd [MYEGPT-HOME-DIRECTORY]`
    
    `docker run --env-file [path-to-dotenv-file] -p 8080:8080 [your-container-name]:[your-tag-name]`

4. Navigate browser to
    
    http://localhost:8080 or http://127.0.0.1:8080


# Publicity

1. Best oral presentation in the Youth Forum for ICBBS 2025 at Xiamen, 18 October.
[![Presentation](https://img.youtube.com/vi/pcfDr0uDm3o/hqdefault.jpg)](https://youtu.be/pcfDr0uDm3o)


# Acknowledgements
- Multiple Myeloma Research Foundation (MMRF) 
- Participants of the CoMMpass trial (NCT01454297)
- Prof Chng Wee Joo, CSI, NUS for research funding

# License
- This project is open source under [Dual Licensing](LICENSE.md)
