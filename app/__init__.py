from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.markdown import Markdown

app = Flask(__name__)
app.config.from_pyfile('settings.cfg')
Markdown(app)
db = SQLAlchemy(app)

from app import database
from app import views
