from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize SQLAlchemy
db = SQLAlchemy()

def init_app(app):
    """Initialize the database with the Flask app"""
    # Database configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
        'DATABASE_URL', 
        'sqlite:///go2news.db'  # Default to SQLite for development
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize extensions
    db.init_app(app)
    Migrate(app, db)
    
    return db

def create_tables():
    """Create all database tables"""
    with db.app.app_context():
        db.create_all() 