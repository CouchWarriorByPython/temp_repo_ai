import re
from typing import List

from logger import get_logger

logger = get_logger(__name__)


def clean_html_text(text: str) -> str:
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


def split_snippet_to_bullets(snippet: str, max_length: int = 120) -> List[str]:
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


def get_file_emoji(filename: str) -> str:
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


def extract_filename_from_title(title: str) -> str:
    """Витягає ім'я файлу з title та додає розширення якщо його немає."""
    if not title:
        return "Документ"

    # Якщо вже є розширення - повертаємо як є
    if '.' in title and any(ext in title.lower() for ext in ['.pdf', '.xlsx', '.xls', '.csv', '.doc', '.docx', '.txt']):
        return title

    # Якщо немає розширення - додаємо .pdf як default
    return f"{title}.pdf"


def format_summary(summary_text: str) -> str:
    """Форматує summary з правильними переносами рядків, розбиває на окремі bullet points."""
    if not summary_text:
        return ""

    logger.info(f"🔧 Початковий summary (перші 200 символів): {summary_text[:200]}...")

    # Очищуємо HTML
    clean_summary = clean_html_text(summary_text)

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