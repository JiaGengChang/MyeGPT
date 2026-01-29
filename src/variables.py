import os

API_BYPASS_TOKEN=os.environ.get("API_BYPASS_TOKEN")
DBHOSTNAME=os.environ.get("DBHOSTNAME")
DBUSERNAME=os.environ.get("DBUSERNAME")
DBPASSWORD=os.environ.get("DBPASSWORD")
MODEL_ID=os.environ.get("MODEL_ID")
MAIL_USERNAME=os.environ.get("MAIL_USERNAME")
MAIL_PASSWORD=os.environ.get("MAIL_PASSWORD")
MAIL_SERVER=os.environ.get("MAIL_SERVER")
SERVER_BASE_URL=os.environ.get("SERVER_BASE_URL")
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
JWT_SECURITY_SALT = os.environ.get("JWT_SECURITY_SALT")
EMBEDDINGS_MODEL_PROVIDER = os.environ.get("EMBEDDINGS_MODEL_PROVIDER")
EMBEDDINGS_TABLE_SUFFIX = os.environ.get("EMBEDDINGS_TABLE_SUFFIX")

assert API_BYPASS_TOKEN is not None, "API_BYPASS_TOKEN environment variable is not set"
assert DBHOSTNAME is not None, "DBHOSTNAME environment variable is not set"
assert DBUSERNAME is not None, "DBUSERNAME environment variable is not set"
assert DBPASSWORD is not None, "DBPASSWORD environment variable is not set"
assert MODEL_ID is not None, "MODEL_ID environment variable is not set"
assert MAIL_USERNAME is not None, "MAIL_USERNAME environment variable is not set"
assert MAIL_PASSWORD is not None, "MAIL_PASSWORD environment variable is not set"
assert MAIL_SERVER is not None, "MAIL_SERVER environment variable is not set"
assert SERVER_BASE_URL is not None, "SERVER_BASE_URL environment variable is not set"
assert JWT_SECRET_KEY is not None, "JWT_SECRET_KEY environment variable is not set"
assert JWT_SECURITY_SALT is not None, "JWT_SECURITY_SALT environment variable is not set"
assert EMBEDDINGS_MODEL_PROVIDER is not None, "EMBEDDINGS_MODEL_PROVIDER environment variable is not set"
assert EMBEDDINGS_TABLE_SUFFIX is not None, "EMBEDDINGS_TABLE_SUFFIX environment variable is not set"

# derived variables
COMMPASS_DSN=f"dbname=commpass user={DBUSERNAME} password={DBPASSWORD} host={DBHOSTNAME} port=5432"
COMMPASS_AUTH_DSN=f"dbname=commpass user={DBUSERNAME} password={DBPASSWORD} host={DBHOSTNAME} options='-c search_path=auth'"
COMMPASS_DB_URI=f"postgresql+psycopg://{DBUSERNAME}:{DBPASSWORD}@{DBHOSTNAME}/commpass"
COMMPASS_DB_URI_POSTGRES=f"postgresql+psycopg://{DBUSERNAME}:{DBPASSWORD}@{DBHOSTNAME}/commpass"
COMMPASS_MEMORY_DB_URI=f"postgresql://{DBUSERNAME}:{DBPASSWORD}@{DBHOSTNAME}:5432/commpass?options=-csearch_path%3dcheckpoints"

__all__ = [
    "API_BYPASS_TOKEN",
    "COMMPASS_AUTH_DSN",
    "COMMPASS_DB_URI",
    "COMMPASS_DB_URI_POSTGRES",
    "COMMPASS_DSN",
    "COMMPASS_MEMORY_DB_URI",
    "EMBEDDINGS_MODEL_PROVIDER",
    "EMBEDDINGS_TABLE_SUFFIX",
    "MAIL_USERNAME",
    "MAIL_PASSWORD",
    "MAIL_SERVER",
    "MODEL_ID",
    "SERVER_BASE_URL",
    "JWT_SECRET_KEY",
    "JWT_SECURITY_SALT",
]