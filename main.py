import json
import logging
from typing import Dict, Any

import functions_framework
from flask import jsonify

# Імпортуємо функції пошуку з окремого модуля
from search_functions import search_vertex_ai

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_chat_response(message: str) -> Dict[str, Any]:
    """Створює відповідь для Google Chat."""
    return {
        "text": message
    }


@functions_framework.http
def chat_vertex_bot(request):
    """HTTP Cloud Function для обробки Google Chat webhooks."""

    # Перевірка методу запиту
    if request.method != 'POST':
        return jsonify({"error": "Only POST method allowed"}), 405

    try:
        # Парсинг JSON запиту від Google Chat
        request_json = request.get_json(silent=True)

        if not request_json:
            logger.error("Порожній JSON запит")
            return jsonify({"error": "Invalid JSON"}), 400

        logger.info(f"Отримано запит: {json.dumps(request_json, indent=2)}")

        # Перевірка типу події
        event_type = request_json.get('type')

        if event_type == 'ADDED_TO_SPACE':
            # Покращене вітальне повідомлення
            welcome_message = """🤖 **Vertex AI Search Bot**

Привіт! Я допоможу знайти інформацію в наших документах.

**Як користуватися:**
• Просто напишіть ваш запит
• Я знайду релевантні документи
• Отримаєте структуровані результати з лінками

**Приклади запитів:**
• "імпорт прайсів"
• "налаштування системи" 
• "інструкція з використання"

Спробуйте прямо зараз! 🚀"""

            response = create_chat_response(welcome_message)
            return jsonify(response)

        elif event_type == 'MESSAGE':
            # Обробка повідомлення
            message_text = request_json.get('message', {}).get('text', '').strip()

            if not message_text:
                help_message = """💬 **Як задати запит**

Надішліть текстове повідомлення з вашим запитом.

**Приклади:**
• "документація API"
• "налаштування бази даних"
• "інструкція користувача"

Я знайду відповідні документи та покажу структуровані результати."""

                response = create_chat_response(help_message)
                return jsonify(response)

            # Видаляємо згадку бота якщо є
            if message_text.startswith('<users/'):
                # Формат: <users/123456789012345678901> your query
                parts = message_text.split('> ', 1)
                if len(parts) > 1:
                    message_text = parts[1].strip()
                else:
                    response = create_chat_response(
                        "💡 Напишіть запит після згадки бота.\n\nПриклад: `@bot документація API`")
                    return jsonify(response)

            # Перевіряємо довжину запиту
            if len(message_text) < 3:
                response = create_chat_response(
                    "🔍 **Запит занадто короткий**\n\nБудь ласка, введіть запит довжиною щонайменше 3 символи.")
                return jsonify(response)

            logger.info(f"Пошуковий запит: {message_text}")

            # Виконання пошуку
            search_result = search_vertex_ai(message_text)

            # Повертаємо результат
            response = create_chat_response(search_result)
            return jsonify(response)

        elif event_type == 'REMOVED_FROM_SPACE':
            # Логування видалення бота
            logger.info("Бот був видалений з простору")
            return jsonify({"text": ""}), 200

        else:
            logger.info(f"Невідомий тип події: {event_type}")
            return jsonify({"text": ""}), 200

    except Exception as e:
        logger.error(f"Помилка обробки запиту: {str(e)}")

        error_message = """⚠️ **Внутрішня помилка**

Вибачте, сталася помилка під час обробки запиту.

**Що можна зробити:**
• Спробуйте ще раз через кілька секунд
• Перефразуйте запит
• Зверніться до адміністратора

Код помилки збережено в логах."""

        error_response = create_chat_response(error_message)
        return jsonify(error_response), 500