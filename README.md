# MyeGPT

An agentic conversation application for researchers to mine the MMRF-CoMMpass dataset, built with LangChain.

Designed towards smartphone browsers, it aims to accelerate hypothesis generation among wet-lab researchers by giving access to clinical cohort data at their fingertips.

<img height="800" width="536" alt="Phone site demonstration screenshot" src="https://github.com/user-attachments/assets/8ecc60f5-4d9d-4f6e-8685-0f9b557500be" />


# Demo

1. Clustering of genes

https://github.com/user-attachments/assets/505c548c-2537-49a7-b0bf-9a90729bac8f

2. Heatmap of genes

https://github.com/user-attachments/assets/befa90a9-2669-460a-858d-fff7420ee0e3

3. Survival analysis

https://github.com/user-attachments/assets/3a74c211-d806-4a3e-842a-4453ad5c76d2


# Setup
## Pre-requisite 1. Database

1. Server with PostgreSQL 17.5, with firewall disabled for port `5432`

2. A publicly accessible IPv4 address or domain name

3. Python 3.13 installed on local machine

4. Email repo maintainer for the data folders, namely `refdata`, `omicdata` and `clindata`. These contain flatfiles that will be used to build the database.

Instructions

1. Install requirements.txt e.g., `pip install -r requirements.txt`

1. Populate `.env` file with the `COMMPASS_DB_URI` variable and place it in the `src` folder

2. Run database creation utility

    `cd [MYEGPT-HOME-DIRECTORY]`

    `python create_database.py`

    This script takes ~2 hours due to the large number of entries for gene expression matrix.

3. This will create a database named `commpass`.

## Pre-requisite 2. Mail server

1. Create an email server which the application can use to send emails with. 

    This is needed for email verification as part of account registration. 

    I use Ionos mail because my domain is registered with them. 

2. Provide the following variables in the `.env` file
    ```
    MAIL_USERNAME=[admin@your-domain-or-ip-address.com]
    MAIL_PASSWORD=[your-mail-server-password]
    MAIL_FROM=[admin@your-domain-or-ip-address.com]
    MAIL_PORT=587
    MAIL_SERVER=[your.mail.server.provider.com]
    ```

## Pre-requisite 3. LLM/Embedding provider

1. Create and fund a developer account with the following supported LLM providers

    1. OpenAI

    2. Anthropic Claude

    3. Google Gemini AI

    4. AWS (need to enable the Bedrock service)

2. Create a developer account with following embedding service providers

    1. OpenAI

    2. MistralAI

    3. AWS (need to enable the Bedrock service)

    4. Google Gemini AI

3. For path of least resistance, opt for OpenAI for both LLM and text embedding

## Build and deploy

The following terminal commands have only been tested on MacOS Sequioa 15.5

1. Install docker desktop (https://docs.docker.com/desktop/)

2. Build the application

    `docker build -t [your-container-name]:[your-tag-name]` 

    Example `docker build -t myegpt:latest`.

3. Populate `.env` file with your API keys/secrets and place it in the `src` folder

5. Launch the application

    `cd [MYEGPT-HOME-DIRECTORY]`
    
    `docker run --env-file src/.env -p 8080:8080 [your-container-name]:[your-tag-name]`

6. Navigate browser to application address
    
    Either http://localhost:8000 or http://127.0.0.1:8080


# Publicity

1. Best oral presentation in the Youth Forum for ICBBS 2025 at Xiamen, 18 October.
[![Presentation](https://img.youtube.com/vi/pcfDr0uDm3o/hqdefault.jpg)](https://youtu.be/pcfDr0uDm3o)


# Acknowledgements
- Multiple Myeloma Research Foundation (MMRF) 
- Participants of the CoMMpass trial (NCT01454297)
- Prof Chng Wee Joo, CSI, NUS for research funding

# License
- This project is open source under [Dual Licensing](LICENSE.md)
