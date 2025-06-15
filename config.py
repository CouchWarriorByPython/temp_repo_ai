import os
from typing import Optional
from dotenv import load_dotenv

if not os.path.exists('.env'):
    raise FileNotFoundError("❌ .env файл не знайдено!")

load_dotenv()


class Config:
    PROJECT_ID: str = os.getenv("PROJECT_ID")
    LOCATION: str = os.getenv("LOCATION")
    SEARCH_ENGINE_ID: str = os.getenv("SEARCH_ENGINE_ID")
    CODE_VERSION: str = "v1.0.0"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "cloud")

    @property
    def SERVICE_ACCOUNT_FILE(self) -> Optional[str]:
        if self.is_local():
            path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            return path if path and os.path.exists(path) else None
        return None

    def is_local(self) -> bool:
        return self.ENVIRONMENT.lower() == "local"

    def is_cloud(self) -> bool:
        return self.ENVIRONMENT.lower() == "cloud"

    def validate(self) -> None:
        required = ["PROJECT_ID", "LOCATION", "SEARCH_ENGINE_ID"]
        missing = [var for var in required if not getattr(self, var)]

        if missing:
            raise ValueError(f"Відсутні змінні: {', '.join(missing)}")

        if self.is_local() and not self.SERVICE_ACCOUNT_FILE:
            raise ValueError("У локальному середовищі потрібен credentials.json")


config = Config()