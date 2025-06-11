import json
import logging
from typing import Dict, Any, List

import functions_framework
from flask import jsonify, Request

from search_functions import search_vertex_ai_structured

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ВЕРСІЯ КОДУ ДЛЯ КОНТРОЛЮ ДЕПЛОЮ
CODE_VERSION = "v1.4.1-fix-summary-lines"
logger.info(f"🚀 Запуск Chat Bot версії: {CODE_VERSION}")


def create_chat_response(message: str) -> Dict[str, Any]:
    """Створює звичайну текстову відповідь для Google Chat."""
    return {
        "text": message
    }


def create_cards_response(query: str, summary: str, results: List[Dict]) -> Dict[str, Any]:
    """Створює Cards відповідь для Google Chat з клікабельними лінками."""

    logger.info(
        f"🎯 Створення Cards відповіді: query='{query}', summary_length={len(summary) if summary else 0}, results_count={len(results)}")

    cards = []

    # Заголовочна картка
    header_card = {
        "header": {
            "title": "🔍 Результати пошуку",
            "subtitle": f"Запит: {query}",
            "imageUrl": "https://fonts.gstatic.com/s/i/short-term/release/googlesymbols/search/default/24px.svg"
        }
    }
    cards.append(header_card)

    # Summary картка якщо є
    if summary:
        summary_lines = [line.strip() for line in summary.split('\n') if line.strip()]
        summary_widgets = []

        for line in summary_lines:
            if line.startswith('•'):
                summary_widgets.append({
                    "textParagraph": {
                        "text": f"<b>{line}</b>"
                    }
                })

        if summary_widgets:
            summary_card = {
                "sections": [{
                    "header": "📄 Підсумок",
                    "widgets": summary_widgets
                }]
            }
            cards.append(summary_card)

    # Результати картки
    if results:
        logger.info(f"📋 Створення карток для {len(results)} результатів")
        results_widgets = []

        for i, result in enumerate(results, 1):
            title = result.get("title", f"Документ {i}")
            snippet = result.get("snippet", "фрагмент відсутній")
            link = result.get("link", "")

            logger.info(f"  📄 Обробка результату {i}: {title}")

            # Конвертуємо gs:// URL
            if link.startswith("gs://"):
                path = link.replace("gs://", "")
                link = f"https://storage.cloud.google.com/{path}"

            # Обрізаємо snippet для кращого відображення та економії місця
            display_snippet = snippet[:100] + "..." if len(snippet) > 100 else snippet

            # Визначаємо тип файлу для іконки
            file_emoji = "📄"
            if ".xlsx" in title.lower() or ".xls" in title.lower() or ".csv" in title.lower():
                file_emoji = "📊"
            elif ".doc" in title.lower():
                file_emoji = "📝"

            widget = {
                "decoratedText": {
                    "topLabel": f"{file_emoji} Документ {i}",
                    "text": f"<b>{title}</b>",
                    "bottomLabel": display_snippet,
                    "onClick": {
                        "openLink": {
                            "url": link
                        }
                    },
                    "button": {
                        "text": "📎 Відкрити",
                        "onClick": {
                            "openLink": {
                                "url": link
                            }
                        }
                    }
                }
            }

            results_widgets.append(widget)

        logger.info(f"✅ Створено {len(results_widgets)} віджетів для результатів")

        if results_widgets:
            results_card = {
                "sections": [{
                    "header": "📋 Детальні результати",
                    "widgets": results_widgets
                }]
            }
            cards.append(results_card)

    # Поради картка
    tips_card = {
        "sections": [{
            "header": "💡 Поради",
            "widgets": [
                {
                    "textParagraph": {
                        "text": "• Натисніть на назву документа або кнопку для перегляду\n• Уточніть запит для кращих результатів"
                    }
                }
            ]
        }]
    }
    cards.append(tips_card)

    # Перевіряємо розмір відповіді
    response_data = {
        "cardsV2": [{"card": card} for card in cards]
    }

    # Приблизна оцінка розміру JSON
    import json
    response_size = len(json.dumps(response_data, ensure_ascii=False))
    logger.info(f"📊 Розмір Cards відповіді: {response_size} байт (ліміт: 30000)")
    logger.info(f"📊 Кількість карток: {len(cards)}")

    # Якщо занадто великий - обрізаємо результати
    if response_size > 30000:  # 30KB safety margin
        logger.warning(f"⚠️ Відповідь занадто велика ({response_size} байт), обрізаємо результати")
        # Залишаємо тільки header, summary і перші 3 результати
        trimmed_cards = cards[:2]  # header + summary
        logger.info(
            f"🔄 Залишаємо перші 2 картки: {[card.get('header', {}).get('title', 'Unknown') for card in trimmed_cards]}")

        if len(cards) > 2:  # якщо є результати
            # Беремо results card і обрізаємо widgets
            results_card = cards[2].copy()
            if 'sections' in results_card and len(results_card['sections']) > 0:
                original_widgets = results_card['sections'][0].get('widgets', [])
                results_card['sections'][0]['widgets'] = original_widgets[:3]  # тільки 3 результати
                logger.info(f"✂️ Обрізаємо результати з {len(original_widgets)} до 3 віджетів")
            trimmed_cards.append(results_card)

        response_data = {
            "cardsV2": [{"card": card} for card in trimmed_cards]
        }

        final_size = len(json.dumps(response_data, ensure_ascii=False))
        logger.info(f"📉 Обрізана відповідь: {final_size} байт")
    else:
        logger.info(f"✅ Розмір відповіді в межах норми, відправляємо всі {len(cards)} карток")

    return response_data


@functions_framework.http
def chat_vertex_bot(request: Request):
    """HTTP Cloud Function для обробки Google Chat webhooks."""

    # ДОДАНО: Debug endpoint для тестування
    if request.method == 'GET' and 'debug' in request.args:
        debug_query = request.args.get('q', 'імпорт прайсів')

        # Симулюємо очистку згадки як в реальному Chat
        original_query = debug_query
        if debug_query.startswith('@Vertex AI Search Bot'):
            debug_query = debug_query.replace('@Vertex AI Search Bot', '').strip()

        try:
            search_data = search_vertex_ai_structured(debug_query)
            return jsonify({
                "debug": True,
                "version": CODE_VERSION,
                "prompt_type": "original_user_prompt",
                "original_query": original_query,
                "cleaned_query": debug_query,
                "results_count": len(search_data['results']),
                "summary_length": len(search_data['summary']) if search_data['summary'] else 0,
                "summary_bullets": search_data['summary'].count('•') if search_data['summary'] else 0,
                "results": [{"title": r['title'], "has_snippet": bool(r['snippet'])} for r in search_data['results']]
            })
        except Exception as e:
            return jsonify({"debug_error": str(e), "version": CODE_VERSION}), 500

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
            # Вітальна картка
            welcome_cards = {
                "cardsV2": [{
                    "card": {
                        "header": {
                            "title": "🤖 Vertex AI Search Bot",
                            "subtitle": "Вітаємо у боті для пошуку документів!"
                        },
                        "sections": [{
                            "header": "Як користуватися",
                            "widgets": [
                                {
                                    "textParagraph": {
                                        "text": "<b>• Просто напишіть ваш запит</b>\n<b>• Я знайду релевантні документи</b>\n<b>• Отримаєте структуровані результати з лінками</b>"
                                    }
                                }
                            ]
                        }, {
                            "header": "Приклади запитів",
                            "widgets": [
                                {
                                    "textParagraph": {
                                        "text": "• \"імпорт прайсів\"\n• \"налаштування системи\"\n• \"інструкція з використання\""
                                    }
                                }
                            ]
                        }]
                    }
                }]
            }

            return jsonify(welcome_cards)

        elif event_type == 'MESSAGE':
            # Обробка повідомлення
            message_text = request_json.get('message', {}).get('text', '').strip()

            if not message_text:
                help_cards = {
                    "cardsV2": [{
                        "card": {
                            "header": {
                                "title": "💬 Як задати запит",
                                "subtitle": "Надішліть текстове повідомлення"
                            },
                            "sections": [{
                                "widgets": [
                                    {
                                        "textParagraph": {
                                            "text": "<b>Приклади:</b>\n• \"документація API\"\n• \"налаштування бази даних\"\n• \"інструкція користувача\""
                                        }
                                    }
                                ]
                            }]
                        }
                    }]
                }

                return jsonify(help_cards)

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

            # ДОДАНО: Видаляємо згадку бота з початку тексту
            if message_text.startswith('@Vertex AI Search Bot'):
                message_text = message_text.replace('@Vertex AI Search Bot', '').strip()
                logger.info(f"🧹 Очищено запит від згадки бота: '{message_text}'")

            # Також прибираємо інші можливі варіанти згадок
            if message_text.startswith('@'):
                # Знаходимо перший пробіл після @ і видаляємо все до нього
                parts = message_text.split(' ', 1)
                if len(parts) > 1:
                    message_text = parts[1].strip()
                    logger.info(f"🧹 Очищено загальну згадку: '{message_text}'")

            # Перевіряємо довжину запиту
            if len(message_text) < 3:
                response = create_chat_response(
                    "🔍 **Запит занадто короткий**\n\nБудь ласка, введіть запит довжиною щонайменше 3 символи.")
                return jsonify(response)

            logger.info(f"Пошуковий запит: {message_text}")

            # Виконання пошуку
            try:
                # ВИКОРИСТОВУЄМО НОВУ СТРУКТУРОВАНУ ФУНКЦІЮ
                search_data = search_vertex_ai_structured(message_text)

                # ДОДАЄМО ДЕТАЛЬНЕ ЛОГУВАННЯ
                logger.info(f"🔍 Отримано від Vertex AI:")
                logger.info(f"  📊 Кількість результатів: {len(search_data['results'])}")
                logger.info(f"  📝 Summary довжина: {len(search_data['summary']) if search_data['summary'] else 0}")
                logger.info(f"  📄 Назви документів: {[r['title'] for r in search_data['results']]}")

                # ВИПРАВЛЕНО: Збільшуємо кількість результатів для Cards API
                # Cards API може обробити більше ніж текст
                response = create_cards_response(
                    query=search_data["query"],
                    summary=search_data["summary"],
                    results=search_data["results"]
                )

                logger.info(f"✅ Успішно створено Cards відповідь з {len(search_data['results'])} результатами")
                return jsonify(response)

            except Exception as search_error:
                logger.error(f"Помилка пошуку: {str(search_error)}")

                error_cards = {
                    "cardsV2": [{
                        "card": {
                            "header": {
                                "title": "⚠️ Помилка пошуку",
                                "subtitle": "Сталася помилка під час пошуку"
                            },
                            "sections": [{
                                "widgets": [
                                    {
                                        "textParagraph": {
                                            "text": f"<b>Помилка:</b> {str(search_error)}\n\n<b>Що можна зробити:</b>\n• Спробуйте ще раз через кілька секунд\n• Перефразуйте запит\n• Зверніться до адміністратора"
                                        }
                                    }
                                ]
                            }]
                        }
                    }]
                }

                return jsonify(error_cards), 500

        elif event_type == 'REMOVED_FROM_SPACE':
            # Логування видалення бота
            logger.info("Бот був видалений з простору")
            return jsonify({"text": ""}), 200

        else:
            logger.info(f"Невідомий тип події: {event_type}")
            return jsonify({"text": ""}), 200

    except Exception as e:
        logger.error(f"Помилка обробки запиту: {str(e)}")

        error_cards = {
            "cardsV2": [{
                "card": {
                    "header": {
                        "title": "⚠️ Внутрішня помилка",
                        "subtitle": "Сталася помилка під час обробки запиту"
                    },
                    "sections": [{
                        "widgets": [
                            {
                                "textParagraph": {
                                    "text": "<b>Що можна зробити:</b>\n• Спробуйте ще раз через кілька секунд\n• Перефразуйте запит\n• Зверніться до адміністратора"
                                }
                            }
                        ]
                    }]
                }
            }]
        }

        return jsonify(error_cards), 500