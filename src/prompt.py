import os
import ftplib
from dbdesc import readlines_ftp

# Connect to FTP server and retrieve prompt.txt from prompt folder
with ftplib.FTP() as ftp:
    ftp.connect(os.environ.get("FTP_HOST"))
    ftp.login(os.environ.get("FTP_USERNAME"), os.environ.get("FTP_PASSWORD"))
    ftp.cwd('prompt')
    latent_system_message = readlines_ftp(ftp, "prompt.txt")