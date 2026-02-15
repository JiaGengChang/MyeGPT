# Setup instructions

This is a guide for deploying your own copy of MyeGPT, or adapting it to your own dataset. 

There is already a ready-to-use version mentioned in this repo.

# Pre-requisites
1. Install docker with privileged access

1. Create a python 3.13 virtual environment

2. Install requirements.txt

# Step 1. Database

1. Email repo maintainer for how to setup the database

2. Set the environment variables
    ```
    DBHOSTNAME=[link.to.your.database.com]
    DBUSERNAME=[dbuser]
    DBPASSWORD=[yoursecurepassword]
    ```

# Step 2. Setup Mail server

1. Create an email server which the application can use to send emails with. 

    This is needed for email verification as part of account registration. 

2. Set the following environment variables
    ```
    MAIL_USERNAME=[admin@your-domain.com]
    MAIL_PASSWORD=[your-mail-server-password]
    MAIL_SERVER=[smtp.your-mail-service-provider.com]
    ```

# Step 3. API keys

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

# Step 4. Build and deploy

1. Build the application

    `docker build -t myegpt:latest` 

2. Populate `.env` file with your API keys/secrets. Refer to `src/example.env` for the variables.

3. Launch the application

    `cd [MYEGPT-HOME-DIRECTORY]`
    
    `docker run --env-file [path-to-dotenv-file] -p 8080:8080 myegpt:latest`

4. Navigate browser to
    
    http://localhost:8080 or http://127.0.0.1:8080
