from typing import Dict, Optional, Any
from google.cloud import discoveryengine_v1
from google.oauth2 import service_account
from google.auth import default
from config import config
from logger import get_logger

logger = get_logger(__name__)


class GCPClients:
    _instance: Optional['GCPClients'] = None
    _clients: Optional[Dict[str, Any]] = None
    _credentials = None

    def __new__(cls) -> 'GCPClients':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._clients = None
            cls._instance._credentials = None
        return cls._instance

    def __init__(self) -> None:
        if self._clients is None:
            self._initialize_clients()

    def _initialize_clients(self) -> None:
        logger.info(f"🔧 Ініціалізація GCP клієнтів: {config.ENVIRONMENT}")

        try:
            if config.SERVICE_ACCOUNT_FILE:
                logger.info("🏠 Service Account режим")
                self._credentials = service_account.Credentials.from_service_account_file(
                    config.SERVICE_ACCOUNT_FILE
                )
            else:
                logger.info("☁️ Application Default Credentials")
                self._credentials, _ = default()
        except Exception as e:
            logger.error(f"❌ Помилка ініціалізації credentials: {e}")
            raise

        self._clients = {}

    def _create_discovery_engine_client(self) -> discoveryengine_v1.SearchServiceClient:
        try:
            client_options = {"api_endpoint": f"{config.LOCATION}-discoveryengine.googleapis.com"}
            return discoveryengine_v1.SearchServiceClient(
                credentials=self._credentials,
                client_options=client_options
            )
        except Exception as e:
            logger.error(f"❌ Помилка створення Discovery Engine клієнта: {e}")
            raise

    def get_client(self, client_type: str) -> Any:
        if client_type not in self._clients:
            if client_type == 'discovery_engine':
                self._clients[client_type] = self._create_discovery_engine_client()
            else:
                raise ValueError(f"Невідомий тип клієнта: {client_type}")
        return self._clients[client_type]

    def get_search_client(self) -> discoveryengine_v1.SearchServiceClient:
        return self.get_client('discovery_engine')


clients = GCPClients()