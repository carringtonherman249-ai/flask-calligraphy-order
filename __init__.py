import os
from flask import Flask

def create_app():
    app = Flask(__name__, template_folder='templates', static_folder='static')

    # 配置上传文件夹
    app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

    # 确保上传目录存在
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # 数据库路径
    app.config['DATABASE'] = os.path.join(app.instance_path, 'orders.db')
    os.makedirs(app.instance_path, exist_ok=True)

    # DeepSeek API Key（从环境变量读取）
    app.config['DEEPSEEK_API_KEY'] = os.environ.get('DEEPSEEK_API_KEY', 'your-api-key-here')

    from app import views
    app.register_blueprint(views.bp)

    return app