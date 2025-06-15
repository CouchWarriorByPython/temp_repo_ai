import json
from typing import Dict, Any, List
import functions_framework
from flask import jsonify, Request
from config import config
from logger import get_logger
from search_functions import search_vertex_ai_structured

logger = get_logger(__name__)

try:
    config.validate()
    logger.info("✅ Конфігурація валідна")
except Exception as e:
    logger.error(f"❌ Помилка конфігурації: {e}")
    raise

logger.info(f"🚀 Запуск Chat Bot версії: {config.CODE_VERSION}")


def create_chat_response(message: str) -> Dict[str, Any]:
    return {"text": message}


def create_cards_response(query: str, summary: str, results: List[Dict]) -> Dict[str, Any]:
    logger.info(f"🎯 Створення Cards відповіді: query='{query}', results_count={len(results)}")

    cards = [
        {
            "header": {
                "title": "🔍 Результати пошуку",
                "subtitle": f"Запит: {query}",
                "imageUrl": "https://fonts.gstatic.com/s/i/short-term/release/googlesymbols/search/default/24px.svg"
            }
        }
    ]

    if summary:
        summary_lines = [line.strip() for line in summary.split('\n') if line.strip()]
        summary_widgets = [
            {"textParagraph": {"text": f"<b>{line}</b>"}}
            for line in summary_lines if line.startswith('•')
        ]

        if summary_widgets:
            cards.append({
                "sections": [{
                    "header": "📄 Підсумок",
                    "widgets": summary_widgets
                }]
            })

    if results:
        results_widgets = []

        for i, result in enumerate(results, 1):
            title = result.get("title", f"Документ {i}")
            snippet = result.get("snippet", "фрагмент відсутній")
            link = result.get("link", "")

            if link.startswith("gs://"):
                path = link.replace("gs://", "")
                link = f"https://storage.cloud.google.com/{path}"

            display_snippet = snippet[:100] + "..." if len(snippet) > 100 else snippet

            file_emoji = "📄"
            if any(ext in title.lower() for ext in [".xlsx", ".xls", ".csv"]):
                file_emoji = "📊"
            elif ".doc" in title.lower():
                file_emoji = "📝"

            widget = {
                "decoratedText": {
                    "topLabel": f"{file_emoji} Документ {i}",
                    "text": f"<b>{title}</b>",
                    "bottomLabel": display_snippet,
                    "onClick": {"openLink": {"url": link}},
                    "button": {
                        "text": "📎 Відкрити",
                        "onClick": {"openLink": {"url": link}}
                    }
                }
            }
            results_widgets.append(widget)

        if results_widgets:
            cards.append({
                "sections": [{
                    "header": "📋 Детальні результати",
                    "widgets": results_widgets
                }]
            })

    cards.append({
        "sections": [{
            "header": "💡 Поради",
            "widgets": [{
                "textParagraph": {
                    "text": "• Натисніть на назву документа або кнопку для перегляду\n• Уточніть запит для кращих результатів"
                }
            }]
        }]
    })

    response_data = {"cardsV2": [{"card": card} for card in cards]}

    response_size = len(json.dumps(response_data, ensure_ascii=False))
    if response_size > 30000:
        logger.warning(f"⚠️ Відповідь занадто велика ({response_size} байт), обрізаємо")
        trimmed_cards = cards[:2]
        if len(cards) > 2:
            results_card = cards[2].copy()
            if 'sections' in results_card and len(results_card['sections']) > 0:
                original_widgets = results_card['sections'][0].get('widgets', [])
                results_card['sections'][0]['widgets'] = original_widgets[:3]
            trimmed_cards.append(results_card)
        response_data = {"cardsV2": [{"card": card} for card in trimmed_cards]}

    return response_data


def clean_message_text(text: str) -> str:
    if text.startswith('<users/'):
        parts = text.split('> ', 1)
        text = parts[1].strip() if len(parts) > 1 else text

    text = text.replace('@Vertex AI Search Bot', '').strip()

    if text.startswith('@'):
        parts = text.split(' ', 1)
        text = parts[1].strip() if len(parts) > 1 else ""

    return text


@functions_framework.http
def chat_vertex_bot(request: Request):
    if request.method == 'GET' and 'debug' in request.args:
        debug_query = request.args.get('q', 'імпорт прайсів')
        cleaned_query = clean_message_text(debug_query)

        try:
            search_data = search_vertex_ai_structured(cleaned_query)
            return jsonify({
                "debug": True,
                "version": config.CODE_VERSION,
                "original_query": debug_query,
                "cleaned_query": cleaned_query,
                "results_count": len(search_data['results']),
                "summary_length": len(search_data['summary']) if search_data['summary'] else 0,
                "summary_bullets": search_data['summary'].count('•') if search_data['summary'] else 0,
                "results": [{"title": r['title'], "has_snippet": bool(r['snippet'])} for r in search_data['results']]
            })
        except Exception as e:
            return jsonify({"debug_error": str(e), "version": config.CODE_VERSION}), 500

    if request.method != 'POST':
        return jsonify({"error": "Only POST method allowed"}), 405

    try:
        request_json = request.get_json(silent=True)
        if not request_json:
            return jsonify({"error": "Invalid JSON"}), 400

        event_type = request_json.get('type')

        if event_type == 'ADDED_TO_SPACE':
            return jsonify({
                "cardsV2": [{
                    "card": {
                        "header": {
                            "title": "🤖 Vertex AI Search Bot",
                            "subtitle": "Вітаємо у боті для пошуку документів!"
                        },
                        "sections": [
                            {
                                "header": "Як користуватися",
                                "widgets": [{"textParagraph": {
                                    "text": "<b>• Просто напишіть ваш запит</b>\n<b>• Я знайду релевантні документи</b>\n<b>• Отримаєте структуровані результати з лінками</b>"}}]
                            },
                            {
                                "header": "Приклади запитів",
                                "widgets": [{"textParagraph": {
                                    "text": "• \"імпорт прайсів\"\n• \"налаштування системи\"\n• \"інструкція з використання\""}}]
                            }
                        ]
                    }
                }]
            })

        elif event_type == 'MESSAGE':
            message_text = request_json.get('message', {}).get('text', '').strip()

            if not message_text:
                return jsonify({
                    "cardsV2": [{
                        "card": {
                            "header": {"title": "💬 Як задати запит", "subtitle": "Надішліть текстове повідомлення"},
                            "sections": [{"widgets": [{"textParagraph": {
                                "text": "<b>Приклади:</b>\n• \"документація API\"\n• \"налаштування бази даних\"\n• \"інструкція користувача\""}}]}]
                        }
                    }]
                })

            message_text = clean_message_text(message_text)

            if len(message_text) < 3:
                return jsonify(create_chat_response(
                    "🔍 **Запит занадто короткий**\n\nБудь ласка, введіть запит довжиною щонайменше 3 символи."
                ))

            logger.info(f"Пошуковий запит: {message_text}")

            try:
                search_data = search_vertex_ai_structured(message_text)
                response = create_cards_response(
                    query=search_data["query"],
                    summary=search_data["summary"],
                    results=search_data["results"]
                )
                return jsonify(response)

            except Exception as search_error:
                logger.error(f"Помилка пошуку: {search_error}")
                return jsonify({
                    "cardsV2": [{
                        "card": {
                            "header": {"title": "⚠️ Помилка пошуку", "subtitle": "Сталася помилка під час пошуку"},
                            "sections": [{"widgets": [{"textParagraph": {
                                "text": f"<b>Помилка:</b> {search_error}\n\n<b>Що можна зробити:</b>\n• Спробуйте ще раз через кілька секунд\n• Перефразуйте запит\n• Зверніться до адміністратора"}}]}]
                        }
                    }]
                }), 500

        elif event_type == 'REMOVED_FROM_SPACE':
            logger.info("Бот видалений з простору")
            return jsonify({"text": ""}), 200

        else:
            logger.info(f"Невідомий тип події: {event_type}")
            return jsonify({"text": ""}), 200

    except Exception as e:
        logger.error(f"Помилка обробки запиту: {e}")
        return jsonify({
            "cardsV2": [{
                "card": {
                    "header": {"title": "⚠️ Внутрішня помилка", "subtitle": "Сталася помилка під час обробки запиту"},
                    "sections": [{"widgets": [{"textParagraph": {
                        "text": "<b>Що можна зробити:</b>\n• Спробуйте ще раз через кілька секунд\n• Перефразуйте запит\n• Зверніться до адміністратора"}}]}]
                }
            }]
        }), 500