import os
import ftplib

# Helper function to read text file through an FTP connection
def readlines_ftp(handle:ftplib.FTP, filename: str) -> str:
    data = []
    handle.retrlines(f'RETR {filename}', data.append)
    return '\n'.join(data)

# Connect to FTP server and retrieve prompt.txt from prompt folder
with ftplib.FTP() as ftp:
    ftp.connect(os.environ.get("FTP_HOST"))
    ftp.login(os.environ.get("FTP_USERNAME"), os.environ.get("FTP_PASSWORD"))
    ftp.cwd('prompt')
    latent_system_message = readlines_ftp(ftp, "prompt.txt")