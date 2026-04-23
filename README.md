# 书法下单系统（微信云托管 Flask）

本项目基于微信云托管官方 Flask 模板改造，实现：

- 前端下单页（质感风格 UI）
- 顶部 AI 写稿助手（免费模式可用，可选接入 OpenRouter 免费模型）
- 客户昵称 + 文本/Word（.docx）/txt 提交并入库
- 字数上限 30000
- 自动金额计算
- 后台订单管理页面（清晰查看客户信息）

## 计费规则

- 抄写费：250 字 = 1 元
- 纸费（非 A4）：3000 字 = 1 元
- 纸费（A4）：1000 字 = 1 元
- 字体：楷宋体 / 行草体 / 宋楷体（宋楷体每 1000 字额外 +2 元）
- 24 小时急单：总价 × 2.5

## 主要路由

- `/`：下单页面
- `/admin/orders`：后台订单管理
- `POST /api/ai/generate`：AI 生成文稿
- `POST /api/orders/calc`：计算金额
- `POST /api/orders`：提交订单
- `GET /api/orders`：读取订单列表

## 环境变量

- `MYSQL_ADDRESS`
- `MYSQL_USERNAME`
- `MYSQL_PASSWORD`
- （可选）`OPENROUTER_API_KEY`：配置后可调用免费模型 `qwen/qwen2.5-7b-instruct:free`

## 本地调试

```bash
# 冲突解决后统一的启动顺序
pip install -r requirements.txt
python init_db.py
python run.py 0.0.0.0 80
```

然后访问 `http://127.0.0.1:80/`。
