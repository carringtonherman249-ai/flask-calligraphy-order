import math
import os
from datetime import datetime

import requests
from docx import Document
from flask import render_template, request

from run import app
from wxcloudrun.dao import (
    delete_counterbyid,
    insert_counter,
    insert_order,
    query_counterbyid,
    query_orders,
    update_counterbyid,
)
from wxcloudrun.model import Counters, CalligraphyOrder
from wxcloudrun.response import make_succ_empty_response, make_succ_response, make_err_response

MAX_CHARS = 30000
ALLOWED_PAPER_TYPES = {"non_a4", "a4"}
ALLOWED_FONT_TYPES = {"楷宋体", "行草体", "宋楷体"}


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/admin/orders')
def admin_orders():
    return render_template('admin_orders.html')


def _extract_text_from_upload(upload_file):
    if upload_file is None or not upload_file.filename:
        return ""

    filename = upload_file.filename.lower()
    if filename.endswith('.txt'):
        return upload_file.read().decode('utf-8', errors='ignore')

    if filename.endswith('.docx'):
        document = Document(upload_file)
        return '\n'.join([paragraph.text for paragraph in document.paragraphs if paragraph.text])

    raise ValueError('仅支持上传 .txt 或 .docx 文件')


def _char_count(text):
    return len(''.join(text.split()))


def _calc_amount(char_count, paper_type, font_type, urgent):
    write_fee = math.ceil(char_count / 250)
    paper_fee = math.ceil(char_count / (3000 if paper_type == 'non_a4' else 1000))
    font_fee = math.ceil(char_count / 1000) * 2 if font_type == '宋楷体' else 0
    subtotal = write_fee + paper_fee + font_fee
    total = subtotal * 2.5 if urgent else subtotal
    return {
        'write_fee': round(write_fee, 2),
        'paper_fee': round(paper_fee, 2),
        'font_fee': round(font_fee, 2),
        'subtotal': round(subtotal, 2),
        'total': round(total, 2),
    }


def _free_ai_generate(prompt):
    api_key = os.environ.get('OPENROUTER_API_KEY', '').strip()
    if api_key:
        try:
            response = requests.post(
                'https://openrouter.ai/api/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json',
                },
                json={
                    'model': 'qwen/qwen2.5-7b-instruct:free',
                    'messages': [
                        {'role': 'system', 'content': '你是书法下单网站的文稿助手，擅长生成优雅中文文本。'},
                        {'role': 'user', 'content': prompt},
                    ],
                    'temperature': 0.7,
                },
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            return data['choices'][0]['message']['content']
        except Exception:
            pass

    return (
        f"【AI草稿】\n主题：{prompt}\n\n"
        "第一段：以简洁而有画面感的语言点明主题，适合书写展示。\n"
        "第二段：延展情感与细节，让整体节奏自然、稳重。\n"
        "第三段：以收束句结尾，形成完整的书写稿。\n\n"
        "提示：如需更正式/古风/祝福语版本，可继续让AI助手改写。"
    )


@app.route('/api/ai/generate', methods=['POST'])
def ai_generate():
    payload = request.get_json(silent=True) or {}
    prompt = (payload.get('prompt') or '').strip()
    if not prompt:
        return make_err_response('请先输入主题或需求')

    result = _free_ai_generate(prompt)
    return make_succ_response({'text': result})


@app.route('/api/orders/calc', methods=['POST'])
def calculate_amount():
    payload = request.get_json(silent=True) or {}
    content = (payload.get('content') or '').strip()
    paper_type = payload.get('paper_type', 'non_a4')
    font_type = payload.get('font_type', '楷宋体')
    urgent = bool(payload.get('urgent', False))

    if paper_type not in ALLOWED_PAPER_TYPES:
        return make_err_response('纸张类型不正确')
    if font_type not in ALLOWED_FONT_TYPES:
        return make_err_response('字体类型不正确')

    char_count = _char_count(content)
    if char_count <= 0:
        return make_err_response('请输入文本后再试')
    if char_count > MAX_CHARS:
        return make_err_response('字数超过上限 30000')

    return make_succ_response({'char_count': char_count, **_calc_amount(char_count, paper_type, font_type, urgent)})


@app.route('/api/orders', methods=['POST'])
def create_order():
    nickname = (request.form.get('nickname') or '').strip()
    content = (request.form.get('content') or '').strip()
    paper_type = request.form.get('paper_type', 'non_a4')
    font_type = request.form.get('font_type', '楷宋体')
    urgent = request.form.get('urgent', 'false').lower() == 'true'

    if not nickname:
        return make_err_response('请先输入下单昵称')
    if paper_type not in ALLOWED_PAPER_TYPES:
        return make_err_response('纸张类型不正确')
    if font_type not in ALLOWED_FONT_TYPES:
        return make_err_response('字体类型不正确')

    try:
        upload_text = _extract_text_from_upload(request.files.get('upload_file'))
    except ValueError as error:
        return make_err_response(str(error))

    merged_content = '\n'.join([part for part in [content, upload_text] if part]).strip()
    char_count = _char_count(merged_content)

    if char_count <= 0:
        return make_err_response('请提供文本内容或上传文件')
    if char_count > MAX_CHARS:
        return make_err_response('字数超过上限 30000')

    amount_info = _calc_amount(char_count, paper_type, font_type, urgent)

    order = CalligraphyOrder(
        nickname=nickname,
        content=merged_content,
        char_count=char_count,
        paper_type=paper_type,
        font_type=font_type,
        urgent=urgent,
        ai_generated=request.form.get('ai_generated', 'false').lower() == 'true',
        amount=amount_info['total'],
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    saved = insert_order(order)
    if saved is None:
        return make_err_response('订单保存失败，请检查数据库配置')

    return make_succ_response({'order_id': saved.id, 'amount': amount_info['total'], 'char_count': char_count})


@app.route('/api/orders', methods=['GET'])
def list_orders():
    items = query_orders(limit=500)
    result = []
    for item in items:
        result.append({
            'id': item.id,
            'nickname': item.nickname,
            'char_count': item.char_count,
            'paper_type': item.paper_type,
            'font_type': item.font_type,
            'urgent': bool(item.urgent),
            'ai_generated': bool(item.ai_generated),
            'amount': float(item.amount),
            'created_at': item.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'content_preview': item.content[:120],
            'content': item.content,
        })
    return make_succ_response(result)


@app.route('/api/count', methods=['POST'])
def count():
    params = request.get_json()
    if 'action' not in params:
        return make_err_response('缺少action参数')

    action = params['action']
    if action == 'inc':
        counter = query_counterbyid(1)
        if counter is None:
            counter = Counters()
            counter.id = 1
            counter.count = 1
            counter.created_at = datetime.now()
            counter.updated_at = datetime.now()
            insert_counter(counter)
        else:
            counter.id = 1
            counter.count += 1
            counter.updated_at = datetime.now()
            update_counterbyid(counter)
        return make_succ_response(counter.count)
    if action == 'clear':
        delete_counterbyid(1)
        return make_succ_empty_response()
    return make_err_response('action参数错误')


@app.route('/api/count', methods=['GET'])
def get_count():
    counter = Counters.query.filter(Counters.id == 1).first()
    return make_succ_response(0) if counter is None else make_succ_response(counter.count)
