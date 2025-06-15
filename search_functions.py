from typing import Dict, Any, List
from google.cloud import discoveryengine_v1

from config import config
from logger import get_logger
from gcp_clients import clients
from utils import clean_html_text, get_file_emoji, extract_filename_from_title, split_snippet_to_bullets, format_summary

# Отримуємо логер для модуля
logger = get_logger(__name__)

# Версія модуля
logger.info(f"📚 Завантажено search_functions версії: {config.CODE_VERSION}")


def _format_search_results(results: List[Dict], query: str, summary: str = None) -> str:
    """Форматує результати пошуку у красивому вигляді з summary."""
    header = f"🔍 Результати пошуку для: `{query}`\n"
    response_parts = [header]

    if summary:
        summary_section = f"\n📄 Підсумок:\n{summary}\n"
        response_parts.append(summary_section)

    if summary:
        response_parts.append("\n📋 Детальні результати:\n")

    formatted_items = []

    for result in results:
        title = result["title"] or "Документ"
        snippet = result["snippet"] or "фрагмент відсутній"
        link = result["link"]

        if link.startswith("gs://"):
            path = link.replace("gs://", "")
            link = f"https://storage.cloud.google.com/{path}"

        filename = extract_filename_from_title(title)
        emoji = get_file_emoji(filename)
        item_text = f"📎 **{filename}**\n{link}\n"

        if snippet and snippet != "фрагмент відсутній":
            snippet_parts = split_snippet_to_bullets(snippet)
            for part in snippet_parts:
                item_text += f"• {part}\n"
        else:
            item_text += f"• _Попередній перегляд недоступний_\n"

        formatted_items.append(item_text.rstrip())

    if formatted_items:
        response_parts.append("\n\n".join(formatted_items))

    footer = "\n\n💡 Поради:\n• Натисніть на назву документа для перегляду\n• Уточніть запит для кращих результатів"
    response_parts.append(footer)

    return "".join(response_parts)


def search_vertex_ai_structured(query: str) -> Dict[str, Any]:
    """Виконує пошук через Vertex AI Search і повертає структуровані дані для Cards API."""
    try:
        # Використовуємо централізований клієнт
        client = clients.get_search_client()

        # Параметри запиту
        serving_config = (
            f"projects/{config.PROJECT_ID}/locations/{config.LOCATION}/collections/default_collection/engines/{config.SEARCH_ENGINE_ID}/servingConfigs/default_search"
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
                summary_text = format_summary(response.summary.summary_text)

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
                            clean_text = clean_html_text(snippet_text)
                            if clean_text:
                                snippet_parts.append(clean_text)

                    snippet = " ".join(snippet_parts)

            # Додаємо розширення до назви файлу якщо його немає
            filename = extract_filename_from_title(title)

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
        # Використовуємо централізований клієнт
        client = clients.get_search_client()

        # Параметри запиту
        serving_config = (
            f"projects/{config.PROJECT_ID}/locations/{config.LOCATION}/collections/default_collection/engines/{config.SEARCH_ENGINE_ID}/servingConfigs/default_search"
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
                            clean_text = clean_html_text(snippet_text)
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
        formatted_summary = format_summary(summary_text) if summary_text else None
        formatted_results = _format_search_results(results, query, formatted_summary)

        logger.info("✅ Текстовий пошук успішно завершено")
        logger.info(f"🎯 Результати для веб-тестера: query='{query}', summary_bullets={formatted_summary.count('•') if formatted_summary else 0}, results_count={len(results)}")
        return formatted_results

    except Exception as e:
        logger.error(f"❌ Помилка пошуку: {str(e)}")
        return f"⚠️ Помилка пошуку\n\nДеталі: {str(e)}\n\nСпробуйте пізніше або зверніться до адміністратора."