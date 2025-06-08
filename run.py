import os

# Встановлюємо шлях до credentials
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "credentials.json"

# Запускаємо функцію через Google Functions Framework
from functions_framework import create_app
import main  # ім'я файлу, де твоя функція

app = create_app("chat_vertex_bot", main)
app.run(debug=True, port=8080)
