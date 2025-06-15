from typing import Dict, Any, List
from google.cloud import discoveryengine_v1
from config import config
from logger import get_logger
from gcp_clients import clients
from utils import clean_html_text, get_file_emoji, extract_filename_from_title, split_snippet_to_bullets, format_summary

logger = get_logger(__name__)


def _create_search_request(query: str) -> discoveryengine_v1.SearchRequest:
    serving_config = (
        f"projects/{config.PROJECT_ID}/locations/{config.LOCATION}/collections/default_collection/"
        f"engines/{config.SEARCH_ENGINE_ID}/servingConfigs/default_search"
    )

    summary_spec = discoveryengine_v1.SearchRequest.ContentSearchSpec.SummarySpec(
        summary_result_count=10,
        include_citations=True,
        ignore_adversarial_query=True,
        ignore_non_summary_seeking_query=True,
        model_spec=discoveryengine_v1.SearchRequest.ContentSearchSpec.SummarySpec.ModelSpec(
            version="stable"
        ),
        model_prompt_spec=discoveryengine_v1.SearchRequest.ContentSearchSpec.SummarySpec.ModelPromptSpec(
            preamble=(
                f"Створіть детальний підсумок українською мовою специфічно для запиту '{query}'. "
                "Використовуйте ТІЛЬКИ релевантну інформацію з результатів пошуку. "
                "Відповідь має бути структурована як список з bullet points, кожен пункт починається з '•'. "
                "Максимум 30 речень. Фокусуйтеся на практичних деталях."
            )
        )
    )

    return discoveryengine_v1.SearchRequest(
        serving_config=serving_config,
        query=query,
        page_size=10,
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


def _process_search_results(response) -> tuple[str, List[Dict]]:
    summary_text = ""
    if hasattr(response, 'summary') and response.summary:
        if hasattr(response.summary, 'summary_text') and response.summary.summary_text:
            summary_text = response.summary.summary_text

    results = []
    for result in response.results:
        document = result.document
        title, snippet, link = "", "", ""

        if hasattr(document, 'derived_struct_data'):
            derived_data = dict(document.derived_struct_data)
            title = derived_data.get("title", "")
            link = derived_data.get("link", "")

            snippets_array = derived_data.get("snippets", [])
            if snippets_array:
                snippet_parts = []
                for snippet_obj in snippets_array:
                    snippet_dict = dict(snippet_obj)
                    if snippet_dict.get("snippet_status") == "SUCCESS":
                        clean_text = clean_html_text(snippet_dict.get("snippet", ""))
                        if clean_text:
                            snippet_parts.append(clean_text)
                snippet = " ".join(snippet_parts)

        filename = extract_filename_from_title(title)
        results.append({
            "title": filename,
            "snippet": snippet or "фрагмент відсутній",
            "link": link
        })

    return summary_text, results


def _format_search_results(results: List[Dict], query: str, summary: str = None) -> str:
    header = f"🔍 Результати пошуку для: `{query}`\n"
    response_parts = [header]

    if summary:
        summary_section = f"\n📄 Підсумок:\n{summary}\n"
        response_parts.append(summary_section)
        response_parts.append("\n📋 Детальні результати:\n")

    formatted_items = []
    for result in results:
        title = result["title"]
        snippet = result["snippet"]
        link = result["link"]

        if link.startswith("gs://"):
            path = link.replace("gs://", "")
            link = f"https://storage.cloud.google.com/{path}"

        filename = extract_filename_from_title(title)
        item_text = f"📎 **{filename}**\n{link}\n"

        if snippet and snippet != "фрагмент відсутній":
            snippet_parts = split_snippet_to_bullets(snippet)
            for part in snippet_parts:
                item_text += f"• {part}\n"
        else:
            item_text += "• _Попередній перегляд недоступний_\n"

        formatted_items.append(item_text.rstrip())

    if formatted_items:
        response_parts.append("\n\n".join(formatted_items))

    footer = "\n\n💡 Поради:\n• Натисніть на назву документа для перегляду\n• Уточніть запит для кращих результатів"
    response_parts.append(footer)

    return "".join(response_parts)


def search_vertex_ai_structured(query: str) -> Dict[str, Any]:
    try:
        client = clients.get_search_client()
        request = _create_search_request(query)
        response = client.search(request=request)

        logger.info("🔍 Виконання пошуку через Vertex AI")

        summary_text, results = _process_search_results(response)

        logger.info("✅ Структурований пошук успішно завершено")

        return {
            "query": query,
            "summary": format_summary(summary_text) if summary_text else "",
            "results": results,
            "total_results": len(results)
        }

    except Exception as e:
        logger.error(f"❌ Помилка структурованого пошуку: {e}")
        raise e


def search_vertex_ai(query: str) -> str:
    try:
        search_data = search_vertex_ai_structured(query)

        if not search_data["results"]:
            return "🔍 Результатів не знайдено\n\nСпробуйте:\n• Перефразувати запит\n• Використати синоніми\n• Скоротити запит"

        formatted_summary = search_data["summary"] if search_data["summary"] else None
        return _format_search_results(search_data["results"], query, formatted_summary)

    except Exception as e:
        logger.error(f"❌ Помилка пошуку: {e}")
        return f"⚠️ Помилка пошуку\n\nДеталі: {e}\n\nСпробуйте пізніше або зверніться до адміністратора."