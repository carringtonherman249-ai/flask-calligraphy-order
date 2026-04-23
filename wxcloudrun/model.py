from datetime import datetime

from wxcloudrun import db


class Counters(db.Model):
    __tablename__ = 'Counters'

    id = db.Column(db.Integer, primary_key=True)
    count = db.Column(db.Integer, default=1)
    created_at = db.Column('createdAt', db.TIMESTAMP, nullable=False, default=datetime.now)
    updated_at = db.Column('updatedAt', db.TIMESTAMP, nullable=False, default=datetime.now, onupdate=datetime.now)


class CalligraphyOrder(db.Model):
    __tablename__ = 'CalligraphyOrder'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nickname = db.Column(db.String(64), nullable=False)
    content = db.Column(db.Text, nullable=False)
    char_count = db.Column(db.Integer, nullable=False)
    paper_type = db.Column(db.String(16), nullable=False)
    font_type = db.Column(db.String(16), nullable=False)
    urgent = db.Column(db.Boolean, nullable=False, default=False)
    ai_generated = db.Column(db.Boolean, nullable=False, default=False)
    amount = db.Column(db.Float, nullable=False)
    created_at = db.Column('createdAt', db.TIMESTAMP, nullable=False, default=datetime.now)
    updated_at = db.Column('updatedAt', db.TIMESTAMP, nullable=False, default=datetime.now, onupdate=datetime.now)
