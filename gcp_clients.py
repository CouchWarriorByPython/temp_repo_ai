import os
from typing import Dict, Optional, Any
from google.cloud import discoveryengine_v1
from google.oauth2 import service_account

from config import config
from logger import get_logger

logger = get_logger(__name__)


class GCPClients:
    """Singleton клас для управління Google Cloud Platform клієнтами."""
    
    _instance: Optional['GCPClients'] = None
    _clients: Optional[Dict[str, Any]] = None
    _credentials = None
    
    def __new__(cls) -> 'GCPClients':
        if cls._instance is None:
            cls._instance = super(GCPClients, cls).__new__(cls)
            cls._instance._clients = None
            cls._instance._credentials = None
        return cls._instance
    
    def __init__(self) -> None:
        if self._clients is None:
            self._initialize_clients()
    
    def _initialize_clients(self) -> None:
        """Ініціалізуємо всі GCP клієнти"""
        logger.info("🔧 Ініціалізація GCP клієнтів...")
        
        if config.is_local():
            try:
                self._credentials = service_account.Credentials.from_service_account_file(
                    config.SERVICE_ACCOUNT_FILE
                )
                logger.info("✅ Використовуємо Service Account credentials")
            except Exception as e:
                logger.error(f"❌ Помилка завантаження Service Account: {e}")
                raise
        else:
            logger.info("☁️ Використовуємо Application Default Credentials")
            self._credentials = None
        
        self._clients = {}
        logger.info("✅ GCP клієнти готові до ініціалізації")
    
    def _create_discovery_engine_client(self) -> discoveryengine_v1.SearchServiceClient:
        """Створює клієнт для Discovery Engine (Vertex AI Search)"""
        try:
            client_options = {"api_endpoint": f"{config.LOCATION}-discoveryengine.googleapis.com"}
            
            if self._credentials:
                client = discoveryengine_v1.SearchServiceClient(
                    credentials=self._credentials,
                    client_options=client_options
                )
            else:
                client = discoveryengine_v1.SearchServiceClient(
                    client_options=client_options
                )
            
            logger.info(f"✅ Discovery Engine клієнт створено для регіону: {config.LOCATION}")
            return client
        except Exception as e:
            logger.error(f"❌ Помилка створення Discovery Engine клієнта: {e}")
            raise
    
    def get_client(self, client_type: str) -> Any:
        """Отримує GCP клієнт за типом з lazy loading."""
        if client_type not in self._clients:
            if client_type == 'discovery_engine':
                self._clients[client_type] = self._create_discovery_engine_client()
            else:
                raise ValueError(f"Невідомий тип клієнта: {client_type}. Підтримувані: ['discovery_engine']")
        
        return self._clients[client_type]
    
    def get_search_client(self) -> discoveryengine_v1.SearchServiceClient:
        """Зручний метод для отримання Search клієнта"""
        return self.get_client('discovery_engine')


clients = GCPClients() 