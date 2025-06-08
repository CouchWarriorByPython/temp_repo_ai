#!/usr/bin/env python3
"""
Простий веб-тестер для Vertex AI Search
"""

import os
import time
from flask import Flask, request, render_template_string
from markupsafe import Markup

# Встановлюємо credentials
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "credentials.json"

from search_functions import search_vertex_ai

app = Flask(__name__)

# HTML шаблон
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="uk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Vertex AI Search Bot - Тестер</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            text-align: center;
            margin-bottom: 30px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 10px;
            font-weight: bold;
            color: #555;
        }
        input[type="text"] {
            width: 100%;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 5px;
            font-size: 16px;
            box-sizing: border-box;
        }
        input[type="text"]:focus {
            border-color: #4285f4;
            outline: none;
        }
        button {
            background-color: #4285f4;
            color: white;
            padding: 12px 30px;
            border: none;
            border-radius: 5px;
            font-size: 16px;
            cursor: pointer;
            transition: background-color 0.3s;
        }
        button:hover {
            background-color: #3367d6;
        }
        .quick-tests {
            margin: 20px 0;
            padding: 15px;
            background-color: #f8f9fa;
            border-radius: 5px;
        }
        .quick-test-btn {
            display: inline-block;
            margin: 5px;
            padding: 8px 15px;
            background-color: #6c757d;
            color: white;
            text-decoration: none;
            border-radius: 3px;
            font-size: 14px;
        }
        .quick-test-btn:hover {
            background-color: #5a6268;
            text-decoration: none;
            color: white;
        }
        .result {
            margin-top: 30px;
            padding: 20px;
            background-color: #f8f9fa;
            border-radius: 5px;
            border-left: 4px solid #4285f4;
        }
        .error {
            background-color: #f8d7da;
            border-left-color: #dc3545;
            color: #721c24;
        }
        .loading {
            text-align: center;
            padding: 20px;
            color: #666;
        }
        .metadata {
            margin-top: 15px;
            padding: 10px;
            background-color: #e9ecef;
            border-radius: 3px;
            font-size: 14px;
            color: #6c757d;
        }
        .raw-data {
            margin-top: 15px;
            padding: 15px;
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 5px;
            max-height: 400px;
            overflow-y: auto;
        }
        .raw-data h4 {
            margin-top: 0;
            color: #495057;
        }
        .raw-data-toggle {
            background: #007bff;
            color: white;
            border: none;
            padding: 5px 10px;
            border-radius: 3px;
            cursor: pointer;
            font-size: 12px;
            margin-top: 10px;
        }
        pre {
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            white-space: pre-wrap;
            word-wrap: break-word;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Vertex AI Search Bot - Тестер</h1>

        <form method="POST">
            <div class="form-group">
                <label for="query">Введіть пошуковий запит:</label>
                <input type="text" id="query" name="query" value="{{ query or '' }}" 
                       placeholder="наприклад: імпорт прайсів" required>
            </div>

            <button type="submit">🔍 Виконати пошук</button>
        </form>

        <div class="quick-tests">
            <strong>Швидкі тести:</strong><br>
            <a href="?q=імпорт прайсів" class="quick-test-btn">імпорт прайсів</a>
            <a href="?q=налаштування системи" class="quick-test-btn">налаштування системи</a>
            <a href="?q=документація API" class="quick-test-btn">документація API</a>
            <a href="?q=етап" class="quick-test-btn">етап</a>
            <a href="?q=інструкція" class="quick-test-btn">інструкція</a>
        </div>

        {% if result %}
        <div class="result {% if error %}error{% endif %}">
            <h3>📄 Результат пошуку{% if query %} для: "{{ query }}"{% endif %}</h3>
            <pre>{{ result }}</pre>

            {% if not error and metadata %}
            <div class="metadata">
                <strong>📊 Метадані:</strong><br>
                • Час виконання: {{ metadata.execution_time }}с<br>
                • Кількість рядків: {{ metadata.lines_count }}<br>
                • Довжина тексту: {{ metadata.text_length }} символів<br>
                • Bullet points: {{ metadata.bullet_count }}<br>
                • Лінків: {{ metadata.links_count }}

                <button class="raw-data-toggle" onclick="toggleRawData()">🔍 Показати/Сховати Raw дані</button>

                <div id="raw-data" class="raw-data" style="display: none;">
                    <h4>🔬 Raw дані від Vertex AI:</h4>
                    <p><em>Дивіться консоль браузера (F12) для детального виводу всіх API даних</em></p>
                    {% if metadata.raw_info %}
                    <pre>{{ metadata.raw_info }}</pre>
                    {% endif %}
                </div>
            </div>
            {% endif %}
        </div>
        {% endif %}

        <div style="margin-top: 40px; text-align: center; color: #666; font-size: 14px;">
            <p>💡 Цей тестер допомагає налаштувати правильний вивід результатів пошуку</p>
            <p>Після успішного тестування можна деплоїти в Cloud Function</p>
        </div>
    </div>
</body>
</html>
"""


@app.route('/', methods=['GET', 'POST'])
def index():
    query = None
    result = None
    error = False
    metadata = None

    if request.method == 'POST':
        query = request.form.get('query', '').strip()
    elif request.method == 'GET':
        query = request.args.get('q', '').strip()

    if query:
        try:
            print(f"🔍 Тестую запит: {query}")

            # Замір часу виконання
            start_time = time.time()
            result = search_vertex_ai(query)
            execution_time = round(time.time() - start_time, 2)

            # Збір метаданих для аналізу
            lines = result.split('\n')
            metadata = {
                'execution_time': execution_time,
                'lines_count': len(lines),
                'text_length': len(result),
                'bullet_count': result.count('•'),
                'links_count': result.count('📎'),
                'raw_info': f"Дивіться консоль терміналу де запущено test_web.py для детального виводу Vertex AI API"
            }

            print(f"✅ Успішно виконано за {execution_time}с")

        except Exception as e:
            result = f"❌ Помилка: {str(e)}\n\nПеревірте:\n• credentials.json існує\n• Права доступу до Vertex AI\n• Інтернет з'єднання"
            error = True
            print(f"❌ Помилка: {e}")

    return render_template_string(
        HTML_TEMPLATE,
        query=query,
        result=result,
        error=error,
        metadata=metadata
    )


@app.route('/health')
def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "vertex-ai-search-tester"}


if __name__ == '__main__':
    # Перевіряємо credentials
    if not os.path.exists("credentials.json"):
        print("❌ Файл credentials.json не знайдено!")
        print("Завантажте service account key з GCP Console")
        exit(1)

    print("🚀 Запуск веб-тестера...")
    print("📍 Відкрийте браузер: http://localhost:8080")
    print("💡 Для зупинки натисніть Ctrl+C")

    app.run(host='0.0.0.0', port=8080, debug=True)