
from dotenv import load_dotenv, find_dotenv
import os

# Get the path to the directory this file is in
BASEDIR = os.path.abspath(os.path.dirname(__file__))
# Connect the path with your 'info.env' file name
load_dotenv(os.path.join(BASEDIR, 'info.env'))

MY_ENV_VAR = os.getenv("EMAIL_PASSWORD")
print(MY_ENV_VAR)