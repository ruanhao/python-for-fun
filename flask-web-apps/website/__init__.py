import logging
from flask import Flask
from logging.handlers import RotatingFileHandler
from .admin import bp as admin_bp
from .api import bp as api_bp

logging.basicConfig(
    handlers=[
        RotatingFileHandler(
            filename="/tmp/app.log",
            maxBytes=10 * 1024 * 1024,  # 10M
            backupCount=5),
        logging.StreamHandler(),  # default to stderr
    ],
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(threadName)s - %(message)s',
    datefmt='%m/%d/%Y %I:%M:%S %p')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.ProductionConfig')
    logger.info(app.config)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(api_bp, url_prefix='/api')
    return app
