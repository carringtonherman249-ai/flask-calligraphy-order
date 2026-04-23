import os
import re
import sqlite3
import qrcode
from io import BytesIO
import base64
from datetime import datetime
from flask import Flask, request, jsonify, render_template, g, send_file
from werkzeug.utils import secure_filename
from docx import Document
from openai import OpenAI

# --- 初始化 Flask 应用 ---
app = Flask(__name__)
# 👇 只改了这里：云托管只能写 /tmp
app.config['UPLOAD_FOLDER'] = '/tmp/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 最大上传 16MB
app.config['DEEPSEEK_API_KEY'] = os.environ.get('DEEPSEEK_API_KEY', 'your-api-key-here')

# 确保上传目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# --- 数据库连接管理 ---
DATABASE = os.path.join(app.instance_path, 'orders.db')
os.makedirs(app.instance_path, exist_ok=True)

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# --- 辅助函数：从 Word 提取文本 ---
def extract_text_from_word(file):
    doc = Document(file)
    return '\n'.join([para.text for para in doc.paragraphs])

# --- 辅助函数：字数统计（含中文、标点）---
def count_words(text):
    if not text:
        return 0
    return len(re.findall(r'[^\s]', text))

# --- 金额计算函数 ---
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

# --- 生成二维码（私域社群）---
def generate_qrcode_base64(data):
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill='black', back_color='white')
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

# ========== 页面路由 ==========
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

# ========== API 路由 ==========

# 提交订单
@app.route('/api/submit', methods=['POST'])
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
            temp_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
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

        qr_url = f"https://work.weixin.qq.com/gm/your-group-link?order_id={order_id}"
        qr_base64 = generate_qrcode_base64(qr_url)

        return jsonify({
            'success': True,
            'order_id': order_id,
            'word_count': word_count,
            'amount': amount,
            'qr_code': qr_base64,
            'message': f'订单提交成功！总字数：{word_count}，费用：¥{amount}'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 获取所有订单（管理后台用）
@app.route('/api/orders', methods=['GET'])
def get_orders():
    db = get_db()
    orders = db.execute(
        'SELECT id, customer_name, style, size, paper_type, deadline, '
        'word_count, amount, created_at FROM orders ORDER BY created_at DESC'
    ).fetchall()
    return jsonify([dict(row) for row in orders])

# 获取单个订单完整内容（含文本）
@app.route('/api/order/<int:order_id>', methods=['GET'])
def get_order_detail(order_id):
    db = get_db()
    order = db.execute(
        'SELECT * FROM orders WHERE id = ?', (order_id,)
    ).fetchone()
    if not order:
        return jsonify({'error': '订单不存在'}), 404
    return jsonify(dict(order))

# 导出 CSV
@app.route('/api/export', methods=['GET'])
def export_csv():
    db = get_db()
    orders = db.execute(
        'SELECT id, customer_name, style, size, paper_type, deadline, '
        'word_count, amount, created_at FROM orders ORDER BY created_at DESC'
    ).fetchall()
    import csv
    from io import StringIO
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['订单ID', '客户姓名', '风格', '字号', '纸张', '交期', '字数', '金额', '提交时间'])
    for o in orders:
        cw.writerow([o['id'], o['customer_name'], o['style'], o['size'],
                     o['paper_type'], o['deadline'], o['word_count'], o['amount'], o['created_at']])
    output = si.getvalue().encode('utf-8-sig')
    return send_file(BytesIO(output), mimetype='text/csv', as_attachment=True, download_name='orders.csv')

# DeepSeek AI 代理接口
@app.route('/api/ai/chat', methods=['POST'])
def ai_chat():
    data = request.json
    prompt = data.get('prompt', '')
    if not prompt:
        return jsonify({'error': '请输入内容'}), 400
    try:
        client = OpenAI(api_key=app.config['DEEPSEEK_API_KEY'], base_url="https://api.deepseek.com")
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        reply = response.choices[0].message.content
        return jsonify({'reply': reply})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 实时字数统计接口（供前端调用）
@app.route('/api/count', methods=['POST'])
def count_text():
    text = request.json.get('text', '')
    word_count = count_words(text)
    return jsonify({'count': word_count})

# ========== 启动入口（只改了这里） ==========
if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=80)
