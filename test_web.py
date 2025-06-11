"""
Простий веб-тестер для Vertex AI Search
"""

import os
import time
from flask import Flask, request, render_template_string
from markupsafe import Markup

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "credentials.json"

from search_functions import search_vertex_ai_structured


def _format_web_results(search_data):
    """Форматує структуровані дані для веб-клієнта як красиві картки."""
    query = search_data["query"]
    summary = search_data["summary"]
    results = search_data["results"]

    html = f'''
    <div class="search-container">
        <div class="search-header">
            <h2>🔍 Результати пошуку</h2>
            <p class="search-query">Запит: <span class="query-text">{query}</span></p>
        </div>
    '''

    # Summary картка
    if summary:
        # Розбиваємо summary на окремі bullet points
        summary_lines = [line.strip() for line in summary.split('\n') if line.strip()]
        formatted_summary = ""

        for line in summary_lines:
            if line.startswith('•'):
                formatted_summary += f'<div class="summary-bullet">{line}</div>\n'
            else:
                formatted_summary += f'<div class="summary-bullet">• {line}</div>\n'

        html += f'''
        <div class="result-card summary-card">
            <div class="card-header">
                <h3>📄 Підсумок</h3>
            </div>
            <div class="card-content">
                {formatted_summary}
            </div>
        </div>
        '''

    # Результати картки
    if results:
        html += f'''
        <div class="result-card">
            <div class="card-header">
                <h3>📋 Детальні результати</h3>
            </div>
            <div class="card-content">
        '''

        for i, result in enumerate(results, 1):
            title = result["title"]
            snippet = result["snippet"]
            link = result["link"]

            # Конвертуємо gs:// URL
            if link.startswith("gs://"):
                path = link.replace("gs://", "")
                link = f"https://storage.cloud.google.com/{path}"

            # Емодзі для типу файлу
            emoji = "📄"
            if ".xlsx" in title.lower() or ".xls" in title.lower() or ".csv" in title.lower():
                emoji = "📊"
            elif ".doc" in title.lower():
                emoji = "📝"

            html += f'''
            <div class="document-card">
                <div class="doc-header">
                    <span class="doc-label">{emoji} Документ {i}</span>
                    <a href="{link}" target="_blank" class="open-btn">📎 Відкрити</a>
                </div>
                <div class="doc-title">{title}</div>
                <div class="doc-snippet">
                    {"• " + snippet if snippet and snippet != "фрагмент відсутній" else "• Попередній перегляд недоступний"}
                </div>
            </div>
            '''

        html += '</div></div>'

    # Поради картка
    html += f'''
        <div class="result-card tips-card">
            <div class="card-header">
                <h3>💡 Поради</h3>
            </div>
            <div class="card-content">
                <span class='bullet'>•</span> Натисніть на кнопку "Відкрити" для перегляду документа<br>
                <span class='bullet'>•</span> Уточніть запит для кращих результатів
            </div>
        </div>
    </div>
    '''

    return html


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
            padding: 14px 16px;
            border: 2px solid #e9ecef;
            border-radius: 8px;
            font-size: 16px;
            box-sizing: border-box;
            transition: all 0.3s ease;
            background: #fff;
        }
        input[type="text"]:focus {
            border-color: #4285f4;
            outline: none;
            box-shadow: 0 0 0 3px rgba(66, 133, 244, 0.1);
            transform: translateY(-1px);
        }
        button {
            background: linear-gradient(135deg, #4285f4 0%, #34a853 100%);
            color: white;
            padding: 14px 32px;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        button:hover {
            background: linear-gradient(135deg, #3367d6 0%, #2d8f47 100%);
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(0,0,0,0.2);
        }
        .quick-tests {
            margin: 25px 0;
            padding: 20px;
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border-radius: 10px;
            border: 1px solid #dee2e6;
        }
        .quick-test-btn {
            display: inline-block;
            margin: 5px;
            padding: 10px 16px;
            background: linear-gradient(135deg, #6c757d 0%, #495057 100%);
            color: white;
            text-decoration: none;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.3s ease;
            border: none;
        }
        .quick-test-btn:hover {
            background: linear-gradient(135deg, #5a6268 0%, #343a40 100%);
            text-decoration: none;
            color: white;
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }

        /* Анімація для завантаження */
        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .result-card {
            animation: fadeInUp 0.5s ease-out;
        }

        .search-header {
            animation: fadeInUp 0.3s ease-out;
        }
        .result {
            margin-top: 30px;
            padding: 0;
            background: transparent;
            border: none;
            border-left: none;
        }
        .error {
            background-color: #f8d7da;
            border-left-color: #dc3545;
            color: #721c24;
            padding: 20px;
            border-radius: 5px;
        }

        /* НОВI СТИЛІ ДЛЯ КАРТОК */
        .search-container {
            max-width: 100%;
        }

        .search-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 20px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }

        .search-header h2 {
            margin: 0 0 8px 0;
            font-size: 24px;
        }

        .search-query {
            margin: 0;
            opacity: 0.9;
        }

        .query-text {
            background: rgba(255,255,255,0.2);
            padding: 4px 8px;
            border-radius: 4px;
            font-weight: bold;
        }

        .result-card {
            background: white;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            margin-bottom: 20px;
            overflow: hidden;
            transition: box-shadow 0.3s ease;
        }

        .result-card:hover {
            box-shadow: 0 4px 16px rgba(0,0,0,0.15);
        }

        .card-header {
            background: #f8f9fa;
            padding: 16px 20px;
            border-bottom: 1px solid #e9ecef;
        }

        .card-header h3 {
            margin: 0;
            color: #495057;
            font-size: 18px;
        }

        .card-content {
            padding: 20px;
            line-height: 1.6;
        }

        .summary-card {
            border-left: 4px solid #28a745;
        }

        .tips-card {
            border-left: 4px solid #ffc107;
        }

        .bullet {
            color: #007bff;
            font-weight: bold;
            margin-right: 8px;
        }

        .summary-bullet {
            margin-bottom: 12px;
            padding: 8px 0;
            line-height: 1.5;
            color: #495057;
        }

        .summary-bullet:last-child {
            margin-bottom: 0;
        }

        .document-card {
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 16px;
            transition: all 0.3s ease;
        }

        .document-card:hover {
            background: #e9ecef;
            transform: translateY(-2px);
        }

        .doc-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }

        .doc-label {
            background: #6c757d;
            color: white;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
        }

        .open-btn {
            background: #007bff;
            color: white !important;
            padding: 8px 16px;
            border-radius: 6px;
            text-decoration: none !important;
            font-size: 14px;
            font-weight: 500;
            transition: background-color 0.3s ease;
            border: none;
            cursor: pointer;
        }

        .open-btn:hover {
            background: #0056b3;
            text-decoration: none !important;
        }

        .doc-title {
            font-weight: bold;
            color: #212529;
            margin-bottom: 8px;
            font-size: 16px;
        }

        .doc-snippet {
            color: #6c757d;
            font-style: italic;
            font-size: 14px;
            line-height: 1.5;
        }

        /* ОНОВЛЕНІ СТИЛІ */
        .loading {
            text-align: center;
            padding: 20px;
            color: #666;
        }
        .metadata {
            margin-top: 20px;
            padding: 15px;
            background: #e3f2fd;
            border-radius: 8px;
            font-size: 14px;
            color: #1565c0;
            border-left: 4px solid #2196f3;
        }
        .raw-data {
            margin-top: 15px;
            padding: 15px;
            background: #f8f9fa;
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
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            margin-top: 10px;
            transition: background-color 0.3s ease;
        }

        .raw-data-toggle:hover {
            background: #0056b3;
        }
    </style>
    <script>
        function toggleRawData() {
            var rawData = document.getElementById('raw-data');
            if (rawData.style.display === 'none') {
                rawData.style.display = 'block';
            } else {
                rawData.style.display = 'none';
            }
        }
    </script>
</head>
<body>
    <div class="container">
        <h1>🤖 Vertex AI Search Bot</h1>
        <p style="text-align: center; color: #666; margin-top: -10px;">Тестувальник пошуку документів</p>

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
            <!-- ВИПРАВЛЕНО: Прибрали <pre> і додали |safe для рендерингу HTML -->
            {{ result|safe }}

            {% if not error and metadata %}
            <div class="metadata">
                <strong>📊 Метадані:</strong><br>
                • Час виконання: {{ metadata.execution_time }}с<br>
                • Кількість рядків: {{ metadata.lines_count }}<br>
                • Довжина тексту: {{ metadata.text_length }} символів<br>
                • Bullet points: {{ metadata.bullet_count }}<br>
                • Кількість результатів: {{ metadata.total_results }}<br>
                • Summary знайдено: {{ "Так" if metadata.has_summary else "Ні" }}

                <button class="raw-data-toggle" onclick="toggleRawData()">🔍 Показати/Сховати додаткову інформацію</button>

                <div id="raw-data" class="raw-data" style="display: none;">
                    <h4>📋 Додаткова інформація:</h4>
                    <p>{{ metadata.raw_info }}</p>
                    <p><em>Дивіться консоль терміналу для детального логування Vertex AI API</em></p>
                </div>
            </div>
            {% endif %}
        </div>
        {% endif %}

        <div style="margin-top: 50px; text-align: center; padding: 25px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 12px;">
            <p style="margin: 0 0 10px 0; font-size: 16px; font-weight: 600;">💡 Vertex AI Search Tester</p>
            <p style="margin: 0; opacity: 0.9;">Після успішного тестування деплойте в Cloud Function для використання в Google Chat</p>
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
            # ВИПРАВЛЕНО: Використовуємо структуровану функцію
            search_data = search_vertex_ai_structured(query)
            execution_time = round(time.time() - start_time, 2)

            # Форматуємо для веб-клієнта
            result = _format_web_results(search_data)

            # ВИПРАВЛЕНО: Використовуємо Markup для безпечного рендерингу HTML
            result = Markup(result)

            # Збір метаданих для аналізу
            metadata = {
                'execution_time': execution_time,
                'lines_count': len(str(result).split('\n')),
                'text_length': len(str(result)),
                'bullet_count': str(result).count('•'),
                'links_count': len(search_data["results"]),
                'total_results': search_data["total_results"],
                'has_summary': bool(search_data["summary"]),
                'raw_info': f"Знайдено {search_data['total_results']} результатів. Summary: {'Так' if search_data['summary'] else 'Ні'}"
            }

            print(f"✅ Успішно виконано за {execution_time}с")

        except Exception as e:
            result = f"❌ Помилка: {str(e)}<br><br>Перевірте:<br>• credentials.json існує<br>• Права доступу до Vertex AI<br>• Інтернет з'єднання"
            error = True
            print(f"❌ Помилка: {e}")

            # Для помилок також використовуємо Markup
            result = Markup(result)

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