import json
import logging
from typing import Dict, Any

import functions_framework
from google.cloud import discoveryengine_v1
from flask import jsonify

# Конфігурація
PROJECT_ID = "dulcet-path-462314-f8"
LOCATION = "eu"
SEARCH_ENGINE_ID = "ai-search-chat-bot_1749399060664"

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def search_vertex_ai(query: str) -> str:
    """Виконує пошук через Vertex AI Search і формує текстову відповідь."""
    try:
        # Ініціалізація клієнта Discovery Engine
        client_options = {"api_endpoint": "eu-discoveryengine.googleapis.com"}
        client = discoveryengine_v1.SearchServiceClient(client_options=client_options)

        # Параметри запиту
        serving_config = (
            f"projects/{PROJECT_ID}/locations/{LOCATION}/collections/default_collection/engines/{SEARCH_ENGINE_ID}/servingConfigs/default_search"
        )

        request = discoveryengine_v1.SearchRequest(
            serving_config=serving_config,
            query=query,
            page_size=3,
            spell_correction_spec=discoveryengine_v1.SearchRequest.SpellCorrectionSpec(
                mode=discoveryengine_v1.SearchRequest.SpellCorrectionSpec.Mode.AUTO
            ),
            content_search_spec=discoveryengine_v1.SearchRequest.ContentSearchSpec(
                snippet_spec=discoveryengine_v1.SearchRequest.ContentSearchSpec.SnippetSpec(
                    return_snippet=True
                )
            )
        )

        # Отримання результатів
        response = client.search(request=request)

        results = []
        for result in response.results:
            document = result.document
            title = document.derived_struct_data.get("title", "")
            snippet = document.derived_struct_data.get("snippet", "")
            link = document.derived_struct_data.get("link", "")

            results.append({
                "title": title,
                "snippet": snippet,
                "link": link
            })

        if not results:
            return "На жаль, не знайдено релевантних результатів для вашого запиту."

        # Форматування відповіді
        formatted_results = []
        for i, result in enumerate(results, 1):
            title = result["title"] or f"Документ {i}"
            snippet = result["snippet"] or "_(фрагмент відсутній)_"
            link = result["link"]

            # Перетворення gs:// на публічне https-посилання (якщо потрібно)
            if link.startswith("gs://"):
                path = link.replace("gs://", "")
                link = f"https://storage.cloud.google.com/{path}"

            text = f"{i}. *{title}*\n_{snippet}_\n📄 [{title}]({link})"
            formatted_results.append(text)

        return "\n\n".join(formatted_results)

    except Exception as e:
        logger.error(f"Помилка пошуку: {str(e)}")
        return "Вибачте, сталася помилка під час пошуку. Спробуйте пізніше."


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
            # Вітальне повідомлення при додаванні бота
            response = create_chat_response(
                "Привіт! 👋 Я AI Search Bot. Напишіть мені запит, і я знайду відповідь через Vertex AI Search."
            )
            return jsonify(response)

        elif event_type == 'MESSAGE':
            # Обробка повідомлення
            message_text = request_json.get('message', {}).get('text', '').strip()

            if not message_text:
                response = create_chat_response("Будь ласка, надішліть текстове повідомлення для пошуку.")
                return jsonify(response)

            # Видаляємо згадку бота якщо є
            if message_text.startswith('<users/'):
                # Формат: <users/123456789012345678901> your query
                parts = message_text.split('> ', 1)
                if len(parts) > 1:
                    message_text = parts[1].strip()
                else:
                    response = create_chat_response("Будь ласка, напишіть запит після згадки бота.")
                    return jsonify(response)

            logger.info(f"Пошуковий запит: {message_text}")

            # Виконання пошуку
            search_result = search_vertex_ai(message_text)

            # Формування відповіді
            response_text = f"🔍 *Результати пошуку для:* {message_text}\n\n{search_result}"
            response = create_chat_response(response_text)

            return jsonify(response)

        else:
            logger.info(f"Невідомий тип події: {event_type}")
            return jsonify({"text": ""}), 200

    except Exception as e:
        logger.error(f"Помилка обробки запиту: {str(e)}")
        error_response = create_chat_response("Вибачте, сталася внутрішня помилка. Спробуйте пізніше.")
        return jsonify(error_response), 500