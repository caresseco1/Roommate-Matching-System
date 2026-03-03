from flask import Flask
from flask_cors import CORS
from app.routes import match_bp
from app.data_loader import load_dataset

def create_app():
    app = Flask(__name__)
    CORS(app)

    load_dataset()
    app.register_blueprint(match_bp)

    return app