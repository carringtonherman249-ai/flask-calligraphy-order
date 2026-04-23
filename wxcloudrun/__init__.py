import pymysql
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

import config

pymysql.install_as_MySQLdb()

app = Flask(__name__, instance_relative_config=True)
app.config['DEBUG'] = config.DEBUG
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://{}:{}@{}/flask_demo'.format(
    config.username,
    config.password,
    config.db_address,
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

from wxcloudrun import views  # noqa: E402

app.config.from_object('config')
