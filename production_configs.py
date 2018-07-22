import os

DEBUG = False
SECRET_KEY = 'production key'  # keep secret
SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')