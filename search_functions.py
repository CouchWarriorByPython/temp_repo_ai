"""
Модуль для Vertex AI Search без functions_framework
Для локального тестування
"""

import logging
from typing import Dict, Any, List
from google.cloud import discoveryengine_v1

# Конфігурація
PROJECT_ID = "dulcet-path-462314-f8"
LOCATION = "eu"
SEARCH_ENGINE_ID = "ai-search-chat-bot_1749399060664"

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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


def _format_search_results(results: List[Dict], query: str) -> str:
    """Форматує результати пошуку у красивому вигляді."""

    # Заголовок з кількістю результатів
    header = f"🔍 **Результати пошуку для:** `{query}`\n"

    formatted_items = []

    for i, result in enumerate(results, 1):
        title = result["title"] or f"Документ {i}"
        snippet = result["snippet"] or "фрагмент відсутній"
        link = result["link"]

        # Перетворення gs:// на публічне https-посилання
        if link.startswith("gs://"):
            path = link.replace("gs://", "")
            link = f"https://storage.cloud.google.com/{path}"

        # Форматування кожного результату
        item_text = f"**{i}. {title}**\n"

        # Додаємо snippet з bullet points для кращої структури
        if snippet and snippet != "фрагмент відсутній":
            # Розбиваємо довгі фрагменти на bullet points
            snippet_parts = _split_snippet_to_bullets(snippet)
            for part in snippet_parts:
                item_text += f"   • {part}\n"
        else:
            item_text += f"   • _Попередній перегляд недоступний_\n"

        # Додаємо лінк з іконкою
        item_text += f"   📎 [Відкрити документ]({link})"

        formatted_items.append(item_text)

    # Збираємо все разом з розділювачами
    full_response = header + "\n" + "\n\n".join(formatted_items)

    # Додаємо футер з порадами
    footer = "\n\n💡 **Поради:**\n• Натисніть на лінк для перегляду повного документа\n• Уточніть запит для кращих результатів"

    return full_response + footer


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
            page_size=5,  # Збільшив до 5 для кращих результатів
            spell_correction_spec=discoveryengine_v1.SearchRequest.SpellCorrectionSpec(
                mode=discoveryengine_v1.SearchRequest.SpellCorrectionSpec.Mode.AUTO
            ),
            content_search_spec=discoveryengine_v1.SearchRequest.ContentSearchSpec(
                snippet_spec=discoveryengine_v1.SearchRequest.ContentSearchSpec.SnippetSpec(
                    return_snippet=True,
                    max_snippet_count=3
                )
            )
        )

        # Отримання результатів
        response = client.search(request=request)

        print("\n" + "="*80)
        print("🔍 ДЕТАЛЬНИЙ ВИВІД ВІДПОВІДІ ВІД VERTEX AI")
        print("="*80)

        # Логування загальної інформації про відповідь
        print(f"📊 Тип response: {type(response)}")
        print(f"📊 Атрибути response: {dir(response)}")

        if hasattr(response, 'results'):
            print(f"📊 Кількість результатів: {len(response.results)}")

        # Логування summary якщо є
        if hasattr(response, 'summary') and response.summary:
            print(f"\n📝 SUMMARY:")
            print(f"   Тип: {type(response.summary)}")
            print(f"   Атрибути: {dir(response.summary)}")
            if hasattr(response.summary, 'summary_text'):
                print(f"   Summary text: {response.summary.summary_text}")

        results = []
        for i, result in enumerate(response.results):
            print(f"\n📄 РЕЗУЛЬТАТ #{i+1}")
            print("-" * 40)
            print(f"Тип result: {type(result)}")
            print(f"Атрибути result: {dir(result)}")

            # Логування document
            document = result.document
            print(f"\nТип document: {type(document)}")
            print(f"Атрибути document: {dir(document)}")

            # Логування derived_struct_data
            if hasattr(document, 'derived_struct_data'):
                print(f"\nТип derived_struct_data: {type(document.derived_struct_data)}")
                print(f"Ключі derived_struct_data: {list(document.derived_struct_data.keys())}")
                print(f"Весь derived_struct_data: {dict(document.derived_struct_data)}")

            # Логування struct_data
            if hasattr(document, 'struct_data'):
                print(f"\nТип struct_data: {type(document.struct_data)}")
                if document.struct_data:
                    print(f"Ключі struct_data: {list(document.struct_data.keys())}")
                    print(f"Весь struct_data: {dict(document.struct_data)}")

            # Логування json_data
            if hasattr(document, 'json_data'):
                print(f"\nТип json_data: {type(document.json_data)}")
                if document.json_data:
                    print(f"json_data: {document.json_data}")

            # Логування content
            if hasattr(document, 'content'):
                print(f"\nТип content: {type(document.content)}")
                if document.content:
                    print(f"content: {document.content}")

            # Витягуємо дані різними способами
            title = ""
            snippet = ""
            link = ""

            # Спробуємо derived_struct_data
            if hasattr(document, 'derived_struct_data'):
                derived_data = dict(document.derived_struct_data)
                title = derived_data.get("title", "")
                link = derived_data.get("link", "")

                # Правильно витягуємо snippets з масиву
                snippets_array = derived_data.get("snippets", [])
                if snippets_array:
                    snippet_parts = []
                    for snippet_obj in snippets_array:
                        snippet_dict = dict(snippet_obj)
                        # Шукаємо текст в різних полях snippet об'єкту
                        for key, value in snippet_dict.items():
                            if isinstance(value, str) and value.strip():
                                snippet_parts.append(value.strip())
                                break  # Беремо перший знайдений текст
                    snippet = " ".join(snippet_parts)

                print(f"\n📎 Витягнуті дані:")
                print(f"   Title: {title}")
                print(f"   Snippet: {snippet}")
                print(f"   Link: {link}")

                # ДЕТАЛЬНЕ ЛОГУВАННЯ SNIPPETS
                if 'snippets' in derived_data:
                    snippets_array = derived_data['snippets']
                    print(f"\n🔍 ДЕТАЛЬНИЙ АНАЛІЗ SNIPPETS:")
                    print(f"   Тип snippets: {type(snippets_array)}")
                    print(f"   Кількість snippets: {len(snippets_array)}")

                    for j, snippet_obj in enumerate(snippets_array):
                        print(f"\n   📝 Snippet #{j+1}:")
                        print(f"      Тип: {type(snippet_obj)}")
                        print(f"      Атрибути: {dir(snippet_obj)}")
                        print(f"      Весь об'єкт: {dict(snippet_obj)}")

                        # Витягуємо всі поля з snippet об'єкту
                        snippet_dict = dict(snippet_obj)
                        for key, value in snippet_dict.items():
                            print(f"      {key}: {value}")

                # Шукаємо додаткові поля
                for key, value in derived_data.items():
                    if key not in ["title", "snippet", "link", "snippets"]:
                        print(f"   Додаткове поле '{key}': {value}")

            results.append({
                "title": title,
                "snippet": snippet,
                "link": link,
                "raw_derived_data": dict(document.derived_struct_data) if hasattr(document, 'derived_struct_data') else {},
                "raw_struct_data": dict(document.struct_data) if hasattr(document, 'struct_data') and document.struct_data else {}
            })

        print("\n" + "="*80)
        print("🏁 КІНЕЦЬ ДЕТАЛЬНОГО ВИВОДУ")
        print("="*80)

        if not results:
            return "🔍 **Результатів не знайдено**\n\nСпробуйте:\n• Перефразувати запит\n• Використати синоніми\n• Скоротити запит"

        # Покращене форматування відповіді
        formatted_results = _format_search_results(results, query)
        return formatted_results

    except Exception as e:
        logger.error(f"Помилка пошуку: {str(e)}")
        return f"⚠️ **Помилка пошуку**\n\nДеталі: {str(e)}\n\nСпробуйте пізніше або зверніться до адміністратора."