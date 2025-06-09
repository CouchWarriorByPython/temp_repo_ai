"""
Модуль для Vertex AI Search з підтримкою Summary для Cloud Function
"""

import logging
import os
import re
from typing import Dict, Any, List
from google.cloud import discoveryengine_v1

# Конфігурація з змінних середовища
PROJECT_ID = os.getenv("PROJECT_ID", "dulcet-path-462314-f8")
LOCATION = os.getenv("LOCATION", "eu")
SEARCH_ENGINE_ID = os.getenv("SEARCH_ENGINE_ID", "ai-search-chat-bot_1749399060664")

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _clean_html_text(text: str) -> str:
    """Очищує HTML теги та спеціальні символи з тексту."""
    if not text:
        return ""

    # Видаляємо HTML теги
    clean_text = re.sub(r'<[^>]+>', '', text)

    # Замінюємо HTML entities
    clean_text = clean_text.replace('&nbsp;', ' ')
    clean_text = clean_text.replace('&#39;', "'")
    clean_text = clean_text.replace('&quot;', '"')
    clean_text = clean_text.replace('&amp;', '&')
    clean_text = clean_text.replace('&lt;', '<')
    clean_text = clean_text.replace('&gt;', '>')

    # Прибираємо зайві пробіли
    clean_text = ' '.join(clean_text.split())

    return clean_text.strip()


def _split_snippet_to_bullets(snippet: str, max_length: int = 120) -> List[str]:
    """Розбиває довгий snippet на bullet points."""
    if len(snippet) <= max_length:
        return [snippet]

    # Розбиваємо по реченнях
    sentences = snippet.split('. ')
    bullets = []
    current_bullet = ""

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        # Додаємо крапку якщо її немає
        if not sentence.endswith('.'):
            sentence += '.'

        # Перевіряємо чи поміститься в поточний bullet
        if len(current_bullet + sentence) <= max_length:
            current_bullet += sentence + " "
        else:
            if current_bullet:
                bullets.append(current_bullet.strip())
            current_bullet = sentence + " "

    # Додаємо останній bullet
    if current_bullet:
        bullets.append(current_bullet.strip())

    return bullets[:3]  # Обмежуємо до 3 bullet points


def _format_summary(summary_text: str) -> str:
    """Форматує summary як bullet points."""
    if not summary_text:
        return ""

    # Очищуємо HTML
    clean_summary = _clean_html_text(summary_text)

    # Розбиваємо на речення та перетворюємо в bullet points
    # Враховуємо різні розділювачі для англійської та української мов
    sentences = []

    # Спочатку розбиваємо по крапці з пробілом
    parts = clean_summary.split('. ')

    for part in parts:
        part = part.strip()
        if part and len(part) > 15:  # Фільтруємо занадто короткі фрагменти
            # Видаляємо посилання на джерела типу [1], [2] тощо
            part = re.sub(r'\[\d+\]', '', part)
            part = part.strip()

            if part:
                if not part.endswith('.'):
                    part += '.'
                sentences.append(part)

    # Формуємо bullet points
    formatted_bullets = []
    for sentence in sentences[:5]:  # Максимум 5 bullet points
        formatted_bullets.append(f"• {sentence}")

    return "\n".join(formatted_bullets)


def _format_search_results(results: List[Dict], query: str, summary: str = None) -> str:
    """Форматує результати пошуку у красивому вигляді з summary."""

    # Заголовок
    header = f"🔍 **Результати пошуку для:** `{query}`\n"

    response_parts = [header]

    # Додаємо summary якщо є
    if summary:
        summary_section = f"\n📄 **Підсумок:**\n{summary}\n"
        response_parts.append(summary_section)

    # Додаємо розділювач перед детальними результатами
    if summary:
        response_parts.append("\n📋 **Детальні результати:**\n")

    formatted_items = []

    for i, result in enumerate(results, 1):
        title = result["title"] or f"Документ {i}"
        snippet = result["snippet"] or "фрагмент відсутній"
        link = result["link"]

        # Перетворення gs:// на публічне https-посилання
        if link.startswith("gs://"):
            path = link.replace("gs://", "")
            link = f"https://storage.cloud.google.com/{path}"

        # ВИПРАВЛЕНО: Лінк інтегрований в заголовок
        item_text = f"**{i}. [{title}]({link})**\n"

        # Додаємо snippet з bullet points для кращої структури
        if snippet and snippet != "фрагмент відсутній":
            # Розбиваємо довгі фрагменти на bullet points
            snippet_parts = _split_snippet_to_bullets(snippet)
            for part in snippet_parts:
                item_text += f"• {part}\n"
        else:
            item_text += f"• _Попередній перегляд недоступний_\n"

        # Видаляємо окремий лінк, тепер він в заголовку
        formatted_items.append(item_text.rstrip())

    # Збираємо все разом
    if formatted_items:
        response_parts.append("\n\n".join(formatted_items))

    # Додаємо футер з порадами
    footer = "\n\n💡 **Поради:**\n• Натисніть на назву документа для перегляду\n• Уточніть запит для кращих результатів"
    response_parts.append(footer)

    return "".join(response_parts)


def search_vertex_ai(query: str) -> str:
    """Виконує пошук через Vertex AI Search з підтримкою Summary."""
    try:
        # Ініціалізація клієнта Discovery Engine
        client_options = {"api_endpoint": f"{LOCATION}-discoveryengine.googleapis.com"}
        client = discoveryengine_v1.SearchServiceClient(client_options=client_options)

        # Параметри запиту
        serving_config = (
            f"projects/{PROJECT_ID}/locations/{LOCATION}/collections/default_collection/engines/{SEARCH_ENGINE_ID}/servingConfigs/default_search"
        )

        # ДОДАНО: Summary Spec для генерації підсумку українською мовою
        summary_spec = discoveryengine_v1.SearchRequest.ContentSearchSpec.SummarySpec(
            summary_result_count=5,  # Кількість результатів для summary
            include_citations=True,  # Включити посилання на джерела
            ignore_adversarial_query=True,  # Ігнорувати шкідливі запити
            ignore_non_summary_seeking_query=True,  # Ігнорувати запити що не потребують summary
            model_spec=discoveryengine_v1.SearchRequest.ContentSearchSpec.SummarySpec.ModelSpec(
                version="stable"  # Використовувати стабільну версію моделі
            ),
            # ДОДАНО: Промт для української мови
            model_prompt_spec=discoveryengine_v1.SearchRequest.ContentSearchSpec.SummarySpec.ModelPromptSpec(
                preamble="Надайте детальний підсумок українською мовою. Використовуйте тільки релевантну інформацію з результатів пошуку, не додавайте додаткової інформації, і використовуйте точно такі ж слова як в результатах пошуку коли це можливо. Відповідь має бути не більше 20 речень. Відповідь має бути відформатована як список з bullet points. Кожен пункт списку має починатися з символу '•'."
            )
        )

        request = discoveryengine_v1.SearchRequest(
            serving_config=serving_config,
            query=query,
            page_size=5,
            # ВИПРАВЛЕНО: language_code належить до SearchRequest, НЕ UserInfo
            language_code="uk-UA",  # Українська мова
            user_info=discoveryengine_v1.UserInfo(
                user_id="chatbot_user",  # Простий ідентифікатор
                time_zone="Europe/Kiev"  # Часова зона
            ),
            spell_correction_spec=discoveryengine_v1.SearchRequest.SpellCorrectionSpec(
                mode=discoveryengine_v1.SearchRequest.SpellCorrectionSpec.Mode.AUTO
            ),
            content_search_spec=discoveryengine_v1.SearchRequest.ContentSearchSpec(
                snippet_spec=discoveryengine_v1.SearchRequest.ContentSearchSpec.SnippetSpec(
                    return_snippet=True,
                    max_snippet_count=3
                ),
                # ДОДАНО: Summary Spec
                summary_spec=summary_spec
            )
        )

        # Отримання результатів
        response = client.search(request=request)

        # Логування для Cloud Function (скорочене)
        logger.info("🔍 Виконання пошуку через Vertex AI")

        # ДОДАНО: Детальне логування Summary
        summary_text = ""
        if hasattr(response, 'summary') and response.summary:
            logger.info("📝 Summary знайдено")

            if hasattr(response.summary, 'summary_text') and response.summary.summary_text:
                summary_text = response.summary.summary_text
                logger.info(f"Summary text довжина: {len(summary_text)}")

                # Логуємо перші 200 символів для дебагу
                logger.info(f"Summary preview: {summary_text[:200]}...")
            else:
                logger.warning("Summary text відсутній")

                # Перевіряємо чому summary відсутній
                if hasattr(response.summary, 'summary_skipped_reasons'):
                    logger.warning(f"Summary skipped reasons: {response.summary.summary_skipped_reasons}")
        else:
            logger.warning("Summary НЕ знайдено")

        # Логування результатів
        if hasattr(response, 'results'):
            logger.info(f"📊 Кількість результатів: {len(response.results)}")

        results = []
        for i, result in enumerate(response.results):
            logger.info(f"📄 Обробка результату #{i + 1}")

            # Логування document
            document = result.document

            # Витягуємо дані
            title = ""
            snippet = ""
            link = ""

            if hasattr(document, 'derived_struct_data'):
                derived_data = dict(document.derived_struct_data)
                title = derived_data.get("title", "")
                link = derived_data.get("link", "")

                # Витягуємо snippets
                snippets_array = derived_data.get("snippets", [])
                if snippets_array:
                    snippet_parts = []

                    for j, snippet_obj in enumerate(snippets_array):
                        snippet_dict = dict(snippet_obj)

                        snippet_status = snippet_dict.get("snippet_status", "")
                        snippet_text = snippet_dict.get("snippet", "")

                        if snippet_status == "SUCCESS" and snippet_text:
                            clean_text = _clean_html_text(snippet_text)
                            if clean_text:
                                snippet_parts.append(clean_text)
                        elif snippet_status == "NO_SNIPPET_AVAILABLE":
                            snippet_parts.append("Попередній перегляд недоступний")

                    snippet = " ".join(snippet_parts)

            results.append({
                "title": title or f"Документ {i + 1}",
                "snippet": snippet or "фрагмент відсутній",
                "link": link
            })

        logger.info("🏁 Завершення обробки результатів")

        if not results:
            return "🔍 **Результатів не знайдено**\n\nСпробуйте:\n• Перефразувати запит\n• Використати синоніми\n• Скоротити запит"

        # Форматування з summary
        formatted_summary = _format_summary(summary_text) if summary_text else None
        formatted_results = _format_search_results(results, query, formatted_summary)

        logger.info("✅ Пошук успішно завершено")
        return formatted_results

    except Exception as e:
        logger.error(f"❌ Помилка пошуку: {str(e)}")
        return f"⚠️ **Помилка пошуку**\n\nДеталі: {str(e)}\n\nСпробуйте пізніше або зверніться до адміністратора."