"""
Модуль для Vertex AI Search з підтримкою Summary для Cloud Function
Версія: v1.2.0-max-results
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

# Версія модуля
SEARCH_MODULE_VERSION = "v1.4.1-fix-summary-lines"
logger.info(f"📚 Завантажено search_functions версії: {SEARCH_MODULE_VERSION}")


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
    """Форматує summary з правильними переносами рядків, розбиває на окремі bullet points."""
    if not summary_text:
        return ""

    logger.info(f"🔧 Початковий summary (перші 200 символів): {summary_text[:200]}...")

    # Очищуємо HTML
    clean_summary = _clean_html_text(summary_text)

    # ПОКРАЩЕНИЙ АЛГОРИТМ: Розбиваємо по патерну ". •" або ". -"
    # Це дозволяє розділити bullet points навіть якщо вони в одному рядку

    # Спочатку додаємо перенос рядка перед кожним bullet point
    clean_summary = re.sub(r'\.\s*([•-])', r'.\n\1', clean_summary)
    clean_summary = re.sub(r'^\s*([•-])', r'\1', clean_summary)  # Перший bullet point

    logger.info(f"🔧 Після розбиття bullet points: {clean_summary[:200]}...")

    # Тепер розбиваємо по рядках
    lines = clean_summary.split('\n')
    logger.info(f"🔧 Кількість рядків після розбиття: {len(lines)}")

    formatted_bullets = []

    for i, line in enumerate(lines):
        line = line.strip()
        if not line or len(line) < 5:
            continue

        logger.info(f"🔧 Обробка рядка {i+1}: {line[:100]}...")

        # Видаляємо посилання на джерела типу [1], [2] тощо
        line = re.sub(r'\[\d+\]', '', line)
        line = line.strip()

        if line:
            # Нормалізуємо bullet points
            if line.startswith('-'):
                line = '•' + line[1:]
            elif not line.startswith('•'):
                line = '• ' + line

            # Прибираємо зайві пробіли після •
            line = re.sub(r'•\s+', '• ', line)

            # Забезпечуємо що закінчується крапкою
            if not line.endswith('.'):
                line += '.'

            formatted_bullets.append(line)

    # Якщо нічого не знайшли, спробуємо розбити по реченнях
    if not formatted_bullets:
        logger.info("🔧 Bullet points не знайдено, розбиваємо по реченнях")
        sentences = clean_summary.split('. ')
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and len(sentence) > 10:
                # Видаляємо посилання на джерела
                sentence = re.sub(r'\[\d+\]', '', sentence)
                sentence = sentence.strip()

                if sentence:
                    if not sentence.endswith('.'):
                        sentence += '.'
                    formatted_bullets.append(f"• {sentence}")

    logger.info(f"🔧 Фінальна кількість bullet points: {len(formatted_bullets)}")

    # Обмежуємо кількість та повертаємо
    result = "\n".join(formatted_bullets[:10])
    logger.info(f"🔧 Фінальний результат (перші 200 символів): {result[:200]}...")

    return result


def _get_file_emoji(filename: str) -> str:
    """Повертає емодзі залежно від типу файлу."""
    filename_lower = filename.lower()

    if '.pdf' in filename_lower:
        return '📄'
    elif any(ext in filename_lower for ext in ['.xlsx', '.xls', '.csv']):
        return '📊'
    elif any(ext in filename_lower for ext in ['.doc', '.docx']):
        return '📝'
    elif any(ext in filename_lower for ext in ['.ppt', '.pptx']):
        return '📊'
    elif any(ext in filename_lower for ext in ['.txt', '.md']):
        return '📄'
    else:
        return '📋'


def _extract_filename_from_title(title: str) -> str:
    """Витягає ім'я файлу з title та додає розширення якщо його немає."""
    if not title:
        return "Документ"

    # Якщо вже є розширення - повертаємо як є
    if '.' in title and any(ext in title.lower() for ext in ['.pdf', '.xlsx', '.xls', '.csv', '.doc', '.docx', '.txt']):
        return title

    # Якщо немає розширення - додаємо .pdf як default
    return f"{title}.pdf"


def _format_search_results(results: List[Dict], query: str, summary: str = None) -> str:
    """Форматує результати пошуку у красивому вигляді з summary."""

    # Заголовок з емодзі
    header = f"🔍 Результати пошуку для: `{query}`\n"

    response_parts = [header]

    # Додаємо summary якщо є з правильним форматуванням
    if summary:
        summary_section = f"\n📄 Підсумок:\n{summary}\n"
        response_parts.append(summary_section)

    # Додаємо розділювач перед детальними результатами
    if summary:
        response_parts.append("\n📋 Детальні результати:\n")

    formatted_items = []

    for result in results:  # Прибрали enumerate оскільки номери не потрібні
        title = result["title"] or "Документ"
        snippet = result["snippet"] or "фрагмент відсутній"
        link = result["link"]

        # Перетворення gs:// на публічне https-посилання
        if link.startswith("gs://"):
            path = link.replace("gs://", "")
            link = f"https://storage.cloud.google.com/{path}"

        # Простий формат для Google Chat - назва файлу + URL
        filename = _extract_filename_from_title(title)
        emoji = _get_file_emoji(filename)

        # Google Chat автоматично зробить URL клікабельним
        item_text = f"📎 **{filename}**\n{link}\n"

        # Додаємо snippet з bullet points для кращої структури
        if snippet and snippet != "фрагмент відсутній":
            # Розбиваємо довгі фрагменти на bullet points
            snippet_parts = _split_snippet_to_bullets(snippet)
            for part in snippet_parts:
                item_text += f"• {part}\n"
        else:
            item_text += f"• _Попередній перегляд недоступний_\n"

        formatted_items.append(item_text.rstrip())

    # Збираємо все разом
    if formatted_items:
        response_parts.append("\n\n".join(formatted_items))

    # Додаємо футер з порадами та емодзі
    footer = "\n\n💡 Поради:\n• Натисніть на назву документа для перегляду\n• Уточніть запит для кращих результатів"
    response_parts.append(footer)

    return "".join(response_parts)


def search_vertex_ai_structured(query: str) -> Dict[str, Any]:
    """Виконує пошук через Vertex AI Search і повертає структуровані дані для Cards API."""
    try:
        # Ініціалізація клієнта Discovery Engine
        client_options = {"api_endpoint": f"{LOCATION}-discoveryengine.googleapis.com"}
        client = discoveryengine_v1.SearchServiceClient(client_options=client_options)

        # Параметри запиту
        serving_config = (
            f"projects/{PROJECT_ID}/locations/{LOCATION}/collections/default_collection/engines/{SEARCH_ENGINE_ID}/servingConfigs/default_search"
        )

        # Summary Spec для генерації підсумку українською мовою
        summary_spec = discoveryengine_v1.SearchRequest.ContentSearchSpec.SummarySpec(
            summary_result_count=10,  # МАКСИМАЛЬНО ЗБІЛЬШЕНО: більше результатів для summary
            include_citations=True,
            ignore_adversarial_query=True,
            ignore_non_summary_seeking_query=True,
            model_spec=discoveryengine_v1.SearchRequest.ContentSearchSpec.SummarySpec.ModelSpec(
                version="stable"
            ),
            model_prompt_spec=discoveryengine_v1.SearchRequest.ContentSearchSpec.SummarySpec.ModelPromptSpec(
                preamble=f"Створіть детальний підсумок українською мовою специфічно для запиту '{query}'. Використовуйте ТІЛЬКИ релевантну інформацію з результатів пошуку, що безпосередньо стосується цього запиту. Не додавайте загальної інформації. Використовуйте точно такі ж слова та терміни як в оригінальних документах. Включіть назви документів-джерел у форматі **назва документа**. Відповідь має бути структурована як список з bullet points, кожен пункт починається з '•'. Максимум 30 речень. Фокусуйтеся на практичних деталях та технічних аспектах запиту."
            )
        )

        request = discoveryengine_v1.SearchRequest(
            serving_config=serving_config,
            query=query,
            page_size=10,  # МАКСИМАЛЬНО ЗБІЛЬШЕНО: до 10 результатів
            language_code="uk-UA",
            user_info=discoveryengine_v1.UserInfo(
                user_id="chatbot_user",
                time_zone="Europe/Kiev"
            ),
            spell_correction_spec=discoveryengine_v1.SearchRequest.SpellCorrectionSpec(
                mode=discoveryengine_v1.SearchRequest.SpellCorrectionSpec.Mode.AUTO
            ),
            content_search_spec=discoveryengine_v1.SearchRequest.ContentSearchSpec(
                snippet_spec=discoveryengine_v1.SearchRequest.ContentSearchSpec.SnippetSpec(
                    return_snippet=True,
                    max_snippet_count=3
                ),
                summary_spec=summary_spec
            )
        )

        # Отримання результатів
        response = client.search(request=request)

        logger.info("🔍 Виконання пошуку через Vertex AI")

        # Обробка Summary
        summary_text = ""
        if hasattr(response, 'summary') and response.summary:
            if hasattr(response.summary, 'summary_text') and response.summary.summary_text:
                summary_text = _format_summary(response.summary.summary_text)

        # Обробка результатів
        results = []
        for idx, result in enumerate(response.results):
            document = result.document
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
                    for snippet_obj in snippets_array:
                        snippet_dict = dict(snippet_obj)
                        snippet_status = snippet_dict.get("snippet_status", "")
                        snippet_text = snippet_dict.get("snippet", "")

                        if snippet_status == "SUCCESS" and snippet_text:
                            clean_text = _clean_html_text(snippet_text)
                            if clean_text:
                                snippet_parts.append(clean_text)

                    snippet = " ".join(snippet_parts)

            # Додаємо розширення до назви файлу якщо його немає
            filename = _extract_filename_from_title(title)

            results.append({
                "title": filename,
                "snippet": snippet or "фрагмент відсутній",
                "link": link
            })

        logger.info("✅ Структурований пошук успішно завершено")
        logger.info(f"🎯 Фінальні результати: query='{query}', summary_bullets={summary_text.count('•') if summary_text else 0}, results_count={len(results)}")

        return {
            "query": query,
            "summary": summary_text,
            "results": results,
            "total_results": len(results)
        }

    except Exception as e:
        logger.error(f"❌ Помилка структурованого пошуку: {str(e)}")
        raise e


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

        # Summary Spec для генерації підсумку українською мовою
        summary_spec = discoveryengine_v1.SearchRequest.ContentSearchSpec.SummarySpec(
            summary_result_count=5,  # Кількість результатів для summary
            include_citations=True,  # Включити посилання на джерела
            ignore_adversarial_query=True,  # Ігнорувати шкідливі запити
            ignore_non_summary_seeking_query=True,  # Ігнорувати запити що не потребують summary
            model_spec=discoveryengine_v1.SearchRequest.ContentSearchSpec.SummarySpec.ModelSpec(
                version="stable"  # Використовувати стабільну версію моделі
            ),
            # Промт для української мови
            model_prompt_spec=discoveryengine_v1.SearchRequest.ContentSearchSpec.SummarySpec.ModelPromptSpec(
                preamble="Надайте детальний підсумок українською мовою. Використовуйте тільки релевантну інформацію з результатів пошуку, не додавайте додаткової інформації, і використовуйте точно такі ж слова як в результатах пошуку коли це можливо. Відповідь має бути не більше 20 речень. Відповідь має бути відформатована як список з bullet points. Кожен пункт списку має починатися з символу '•'."
            )
        )

        request = discoveryengine_v1.SearchRequest(
            serving_config=serving_config,
            query=query,
            page_size=10,  # МАКСИМАЛЬНО ЗБІЛЬШЕНО: синхронізовано з structured функцією
            language_code="uk-UA",  # Українська мова
            user_info=discoveryengine_v1.UserInfo(
                user_id="chatbot_user",
                time_zone="Europe/Kiev"
            ),
            spell_correction_spec=discoveryengine_v1.SearchRequest.SpellCorrectionSpec(
                mode=discoveryengine_v1.SearchRequest.SpellCorrectionSpec.Mode.AUTO
            ),
            content_search_spec=discoveryengine_v1.SearchRequest.ContentSearchSpec(
                snippet_spec=discoveryengine_v1.SearchRequest.ContentSearchSpec.SnippetSpec(
                    return_snippet=True,
                    max_snippet_count=3
                ),
                summary_spec=summary_spec
            )
        )

        # Отримання результатів
        response = client.search(request=request)

        # Логування для Cloud Function (скорочене)
        logger.info("🔍 Виконання пошуку через Vertex AI")

        # Обробка Summary
        summary_text = ""
        if hasattr(response, 'summary') and response.summary:
            logger.info("📝 Summary знайдено")

            if hasattr(response.summary, 'summary_text') and response.summary.summary_text:
                summary_text = response.summary.summary_text
                logger.info(f"Summary text довжина: {len(summary_text)}")
                logger.info(f"Summary preview: {summary_text[:200]}...")
            else:
                logger.warning("Summary text відсутній")

                if hasattr(response.summary, 'summary_skipped_reasons'):
                    logger.warning(f"Summary skipped reasons: {response.summary.summary_skipped_reasons}")
        else:
            logger.warning("Summary НЕ знайдено")

        # Логування результатів з деталями
        if hasattr(response, 'results'):
            logger.info(f"📊 Кількість результатів від Vertex AI: {len(response.results)}")
            if summary_text:
                logger.info(f"📝 Summary довжина: {len(summary_text)} символів")
                logger.info(f"📝 Summary bullet points: {summary_text.count('•')}")
            else:
                logger.info("📝 Summary відсутній")

        results = []
        for idx, result in enumerate(response.results):
            logger.info(f"📄 Обробка результату #{idx + 1}")

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

                    for snippet_idx, snippet_obj in enumerate(snippets_array):
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
                "title": title or "Документ",
                "snippet": snippet or "фрагмент відсутній",
                "link": link
            })

        logger.info("🏁 Завершення обробки результатів")

        if not results:
            return "🔍 Результатів не знайдено\n\nСпробуйте:\n• Перефразувати запит\n• Використати синоніми\n• Скоротити запит"

        # Форматування з summary
        formatted_summary = _format_summary(summary_text) if summary_text else None
        formatted_results = _format_search_results(results, query, formatted_summary)

        logger.info("✅ Текстовий пошук успішно завершено")
        logger.info(f"🎯 Результати для веб-тестера: query='{query}', summary_bullets={formatted_summary.count('•') if formatted_summary else 0}, results_count={len(results)}")
        return formatted_results

    except Exception as e:
        logger.error(f"❌ Помилка пошуку: {str(e)}")
        return f"⚠️ Помилка пошуку\n\nДеталі: {str(e)}\n\nСпробуйте пізніше або зверніться до адміністратора."