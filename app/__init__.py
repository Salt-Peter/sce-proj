from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/test.db'
db = SQLAlchemy(app)
# TODO: setup db schema and data dump https://stackoverflow.com/a/846665/5463404

from app import views

from app import models
