from dotenv import load_dotenv
from flask_migrate import Migrate
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

load_dotenv()

# app = Flask(__name__)


db = SQLAlchemy()
migrate = Migrate()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    telegram_id = db.Column(db.String(100), unique=True)
    name = db.Column(db.String(100))
    points = db.Column(db.Integer, default=0)
    tokens = db.Column(db.Integer, default=0)
    # video_link = db.Column(db.String(200), nullable=True)
    # video_name = db.Column(db.String(100), nullable=True)


class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    video_name = db.Column(db.String(255), nullable=False)
    video_link = db.Column(db.String(255), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)


class GameHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    category = db.Column(db.String(50))
    selections = db.Column(db.String(100))  
    result = db.Column(db.Boolean, default=False) 
    played_at = db.Column(db.DateTime, default=datetime.utcnow)

class GameCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class GameOption(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('game_category.id'), nullable=False)
    option = db.Column(db.String(100), nullable=False)
    category = db.relationship('GameCategory', backref=db.backref('options',lazy=True))

def init_db():
    # db.drop_all()
    db.create_all()