import os
from typing import Optional
from dotenv import load_dotenv

if not os.path.exists('.env'):
    raise FileNotFoundError("❌ .env файл не знайдено! Файл є обов'язковим як для локального, так і для cloud середовища.")

load_dotenv()


class Config:
    """Центральний файл конфігурації проєкту"""
    
    PROJECT_ID: str = os.getenv("PROJECT_ID")
    LOCATION: str = os.getenv("LOCATION")
    SEARCH_ENGINE_ID: str = os.getenv("SEARCH_ENGINE_ID")
    CODE_VERSION: str = "v1.0.0"
    SEARCH_MODULE_VERSION: str = "v1.0.0"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "cloud")
    
    @property
    def SERVICE_ACCOUNT_FILE(self) -> Optional[str]:
        """Повертає шлях до service account файлу тільки для локального середовища"""
        if self.is_local():
            return os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        return None
    
    def is_local(self) -> bool:
        """Перевіряє чи це локальне середовище"""
        return self.ENVIRONMENT.lower() == "local"
    
    def is_cloud(self) -> bool:
        """Перевіряє чи це cloud середовище"""
        return self.ENVIRONMENT.lower() == "cloud"
    
    def validate(self) -> None:
        """Перевіряє наявність обов'язкових змінних"""
        required_vars = {
            "PROJECT_ID": self.PROJECT_ID,
            "LOCATION": self.LOCATION,
            "SEARCH_ENGINE_ID": self.SEARCH_ENGINE_ID,
        }
        
        missing_vars = [var for var, value in required_vars.items() if not value]
        if missing_vars:
            raise ValueError(f"Відсутні обов'язкові змінні середовища: {', '.join(missing_vars)}")
        
        if self.is_local() and not self.SERVICE_ACCOUNT_FILE:
            raise ValueError("У локальному середовищі обов'язкова змінна GOOGLE_APPLICATION_CREDENTIALS")
        
        if self.is_local() and self.SERVICE_ACCOUNT_FILE and not os.path.exists(self.SERVICE_ACCOUNT_FILE):
            raise FileNotFoundError(f"Credentials файл не знайдено: {self.SERVICE_ACCOUNT_FILE}")


config = Config() 