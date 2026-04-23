import os
import re
import sqlite3
from datetime import datetime
from flask import Blueprint, request, jsonify, render_template, current_app, g, send_file
from werkzeug.utils import secure_filename
from docx import Document
from openai import OpenAI
import csv
from io import StringIO, BytesIO

bp = Blueprint('main', __name__)

# ---------- 数据库辅助 ----------
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(current_app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
        # 确保表存在
        g.db.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT NOT NULL,
                style TEXT,
                size TEXT,
                paper_type TEXT,
                deadline TEXT,
                paper_count INTEGER,
                text_content TEXT,
                word_count INTEGER,
                amount REAL,
                created_at TEXT
            )
        ''')
        g.db.commit()
    return g.db

@bp.teardown_app_request
def close_db(error=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# ---------- 工具函数 ----------
def extract_text_from_word(file):
    doc = Document(file)
    return '\n'.join([para.text for para in doc.paragraphs])

def count_words(text):
    if not text:
        return 0
    return len(re.findall(r'[^\s]', text))

def calculate_amount(word_count, deadline_type, paper_count=None):
    writing_fee = word_count / 333.0
    urgency_map = {"1天内": 2.5, "3天内": 1.25, "预约3天后": 1.0}
    urgency_factor = urgency_map.get(deadline_type, 1.0)
    if paper_count is None or paper_count == 0:
        paper_fee = word_count / 2000.0
    else:
        paper_fee = paper_count * 0.5
    total = writing_fee * urgency_factor + paper_fee
    return round(total, 2)

# ---------- 页面路由 ----------
@bp.route('/')
def index():
    return render_template('index.html')

@bp.route('/admin')
def admin():
    return render_template('admin.html')

# ---------- API 路由 ----------
@bp.route('/api/extract-word', methods=['POST'])
def extract_word():
    word_file = request.files.get('word_file')
    if not word_file:
        return jsonify({'error': '未上传文件'}), 400
    try:
        filename = secure_filename(word_file.filename)
        upload_folder = current_app.config['UPLOAD_FOLDER']
        os.makedirs(upload_folder, exist_ok=True)
        temp_path = os.path.join(upload_folder, filename)
        word_file.save(temp_path)
        text = extract_text_from_word(temp_path)
        os.remove(temp_path)
        return jsonify({'text': text})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/count', methods=['POST'])
def count_text():
    text = request.json.get('text', '')
    return jsonify({'count': count_words(text)})

@bp.route('/api/submit', methods=['POST'])
def submit_order():
    try:
        customer_name = request.form.get('customer_name', '').strip()
        style = request.form.get('style', '')
        size = request.form.get('size', '')
        paper_type = request.form.get('paper_type', '')
        deadline = request.form.get('deadline', '')
        paper_count = request.form.get('paper_count', '')
        text_content = request.form.get('text_content', '')
        word_file = request.files.get('word_file')

        if not customer_name:
            return jsonify({'error': '请填写客户姓名'}), 400

        if word_file and word_file.filename:
            filename = secure_filename(word_file.filename)
            upload_folder = current_app.config['UPLOAD_FOLDER']
            os.makedirs(upload_folder, exist_ok=True)
            temp_path = os.path.join(upload_folder, filename)
            word_file.save(temp_path)
            text_content = extract_text_from_word(temp_path)
            os.remove(temp_path)

        word_count = count_words(text_content)

        db = get_db()
        cur = db.execute(
            "SELECT COALESCE(SUM(word_count), 0) FROM orders WHERE customer_name = ?",
            (customer_name,)
        )
        existing_total = cur.fetchone()[0]
        if existing_total + word_count > 30000:
            return jsonify({'error': f'客户 {customer_name} 历史总字数已达 {existing_total} 字，本次 {word_count} 字将超出 30000 字上限'}), 400

        paper_cnt = int(paper_count) if paper_count else None
        amount = calculate_amount(word_count, deadline, paper_cnt)

        created_at = datetime.now().isoformat()
        db.execute(
            '''INSERT INTO orders 
               (customer_name, style, size, paper_type, deadline, paper_count, 
                text_content, word_count, amount, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (customer_name, style, size, paper_type, deadline, paper_cnt,
             text_content, word_count, amount, created_at)
        )
        db.commit()
        order_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]

        return jsonify({
            'success': True,
            'order_id': order_id,
            'word_count': word_count,
            'amount': amount,
            'accounts': [
                {'label': '微信号', 'value': 'zh3110241437'},
                {'label': '微信号', 'value': 'XCS1949749'}
            ],
            'message': f'订单提交成功！总字数：{word_count}，费用：¥{amount}'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/orders', methods=['GET'])
def get_orders():
    db = get_db()
    orders = db.execute(
        'SELECT id, customer_name, style, size, paper_type, deadline, '
        'word_count, amount, created_at FROM orders ORDER BY created_at DESC'
    ).fetchall()
    return jsonify([dict(row) for row in orders])

@bp.route('/api/order/<int:order_id>', methods=['GET'])
def get_order_detail(order_id):
    db = get_db()
    order = db.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
    if not order:
        return jsonify({'error': '订单不存在'}), 404
    return jsonify(dict(order))

@bp.route('/api/export', methods=['GET'])
def export_csv():
    db = get_db()
    orders = db.execute(
        'SELECT id, customer_name, style, size, paper_type, deadline, '
        'word_count, amount, created_at FROM orders ORDER BY created_at DESC'
    ).fetchall()
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['订单ID', '客户姓名', '风格', '字号', '纸张', '交期', '字数', '金额', '提交时间'])
    for o in orders:
        cw.writerow([o['id'], o['customer_name'], o['style'], o['size'],
                     o['paper_type'], o['deadline'], o['word_count'], o['amount'], o['created_at']])
    output = si.getvalue().encode('utf-8-sig')
    return send_file(BytesIO(output), mimetype='text/csv', as_attachment=True, download_name='orders.csv')

@bp.route('/api/ai/chat', methods=['POST'])
def ai_chat():
    data = request.json
    prompt = data.get('prompt', '')
    if not prompt:
        return jsonify({'error': '请输入内容'}), 400
    try:
        client = OpenAI(api_key=current_app.config['DEEPSEEK_API_KEY'], base_url="https://api.deepseek.com")
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        reply = response.choices[0].message.content
        return jsonify({'reply': reply})
    except Exception as e:
        return jsonify({'error': str(e)}), 500