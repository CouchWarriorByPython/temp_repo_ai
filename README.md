# Vertex AI Search Chat Bot

Чат-бот з Vertex AI Search для Google Chat.

## 🏗️ Архітектура

- **`config.py`** - Центральна конфігурація проєкту
- **`logger.py`** - Центральний логер 
- **`gcp_clients.py`** - Управління Google Cloud клієнтами
- **`utils.py`** - Допоміжні функції для обробки даних
- **`search_functions.py`** - Функції пошуку через Vertex AI
- **`main.py`** - Cloud Function для Google Chat webhooks
- **`test_web.py`** - Локальний веб-інтерфейс для тестування

## ⚙️ Налаштування

### Локальне середовище

**Обов'язкові файли:**
- ✅ `.env` файл з налаштуваннями проєкту
- ✅ `credentials.json` файл з Google Cloud авторизацією

**Запуск:**
```bash
# Створення віртуального оточення
python  -m venv venv

# Активація оточення
source venv/bin/activate

# Встановлення залежностей
pip install -r requirements.txt

# Локальне тестування
python test_web.py
```

**Файл .env повинен містити:**
```env
PROJECT_ID=your-project-id
LOCATION=eu
SEARCH_ENGINE_ID=your-search-engine-id
GOOGLE_APPLICATION_CREDENTIALS=credentials.json
ENVIRONMENT=local
LOG_LEVEL=INFO
```

### Cloud Functions

**Для деплою на Cloud Functions:**
- Змініть в `.env` файлі: 
- `GOOGLE_APPLICATION_CREDENTIALS=credentials.json` - закоментуйте цей рядок
- `ENVIRONMENT=cloud`

## 🔄 Налаштування для нового проєкту

При потребі підключити новий проєкт, відредагуйте у `.env` файлі:
- `PROJECT_ID=your-new-project-id`
- `SEARCH_ENGINE_ID=your-new-search-engine-id`
- `LOCATION=eu` - локація може бути інша, дивитись де розгорнутий vertexai

## 📝 Логування

- **Локально**: Детальні логи з часовими мітками
- **Cloud Functions**: Оптимізовані логи для Cloud Logging 