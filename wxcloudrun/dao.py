import logging

from sqlalchemy.exc import OperationalError

from wxcloudrun import db
from wxcloudrun.model import Counters, CalligraphyOrder

logger = logging.getLogger('log')


def query_counterbyid(id):
    try:
        return Counters.query.filter(Counters.id == id).first()
    except OperationalError as e:
        logger.info("query_counterbyid errorMsg=%s", e)
        return None


def delete_counterbyid(id):
    try:
        counter = Counters.query.get(id)
        if counter is None:
            return
        db.session.delete(counter)
        db.session.commit()
    except OperationalError as e:
        logger.info("delete_counterbyid errorMsg=%s", e)


def insert_counter(counter):
    try:
        db.session.add(counter)
        db.session.commit()
    except OperationalError as e:
        logger.info("insert_counter errorMsg=%s", e)


def update_counterbyid(counter):
    try:
        current = query_counterbyid(counter.id)
        if current is None:
            return
        current.count = counter.count
        db.session.commit()
    except OperationalError as e:
        logger.info("update_counterbyid errorMsg=%s", e)


def insert_order(order):
    try:
        db.session.add(order)
        db.session.commit()
        return order
    except OperationalError as e:
        logger.info("insert_order errorMsg=%s", e)
        db.session.rollback()
        return None


def query_orders(limit=200):
    try:
        return CalligraphyOrder.query.order_by(CalligraphyOrder.created_at.desc()).limit(limit).all()
    except OperationalError as e:
        logger.info("query_orders errorMsg=%s", e)
        return []
