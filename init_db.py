"""手动初始化数据库表。

用法:
  python init_db.py
"""

from wxcloudrun import app, db


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    print('数据库表初始化完成')
