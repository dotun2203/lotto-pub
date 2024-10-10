import os

# from dotenv import load_dotenv



basedir = os.path.abspath(os.path.dirname(__file__))

# load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'adedotun2203')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///lotto.db'

class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = "postgresql://dotun2203:qKKUV0lvSRXvsUOeLNvnkhltmSiN31mw@dpg-cs3gl33v2p9s73efmdc0-a.oregon-postgres.render.com/lotto_oazi"

