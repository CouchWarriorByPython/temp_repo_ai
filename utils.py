import re
from typing import List
from logger import get_logger

logger = get_logger(__name__)


def clean_html_text(text: str) -> str:
    if not text:
        return ""

    clean_text = re.sub(r'<[^>]+>', '', text)

    replacements = {
        '&nbsp;': ' ', '&#39;': "'", '&quot;': '"',
        '&amp;': '&', '&lt;': '<', '&gt;': '>'
    }

    for old, new in replacements.items():
        clean_text = clean_text.replace(old, new)

    return ' '.join(clean_text.split()).strip()


def split_snippet_to_bullets(snippet: str, max_length: int = 120) -> List[str]:
    if len(snippet) <= max_length:
        return [snippet]

    sentences = snippet.split('. ')
    bullets, current_bullet = [], ""

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        if not sentence.endswith('.'):
            sentence += '.'

        if len(current_bullet + sentence) <= max_length:
            current_bullet += sentence + " "
        else:
            if current_bullet:
                bullets.append(current_bullet.strip())
            current_bullet = sentence + " "

    if current_bullet:
        bullets.append(current_bullet.strip())

    return bullets[:3]


def get_file_emoji(filename: str) -> str:
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
    return '📋'


def extract_filename_from_title(title: str) -> str:
    if not title:
        return "Документ"

    if '.' in title and any(ext in title.lower() for ext in ['.pdf', '.xlsx', '.xls', '.csv', '.doc', '.docx', '.txt']):
        return title

    return f"{title}.pdf"


def format_summary(summary_text: str) -> str:
    if not summary_text:
        return ""

    clean_summary = clean_html_text(summary_text)
    clean_summary = re.sub(r'\.\s*([•-])', r'.\n\1', clean_summary)
    clean_summary = re.sub(r'^\s*([•-])', r'\1', clean_summary)

    lines = clean_summary.split('\n')
    formatted_bullets = []

    for line in lines:
        line = line.strip()
        if not line or len(line) < 5:
            continue

        line = re.sub(r'\[\d+\]', '', line).strip()

        if line:
            if line.startswith('-'):
                line = '•' + line[1:]
            elif not line.startswith('•'):
                line = '• ' + line

            line = re.sub(r'•\s+', '• ', line)

            if not line.endswith('.'):
                line += '.'

            formatted_bullets.append(line)

    if not formatted_bullets:
        sentences = clean_summary.split('. ')
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and len(sentence) > 10:
                sentence = re.sub(r'\[\d+\]', '', sentence).strip()
                if sentence:
                    if not sentence.endswith('.'):
                        sentence += '.'
                    formatted_bullets.append(f"• {sentence}")

    return "\n".join(formatted_bullets[:10])