FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 创建必要目录
RUN mkdir -p uploads instance

ENV FLASK_APP=app.py
ENV DEEPSEEK_API_KEY=your-api-key-here

EXPOSE 5000

CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]