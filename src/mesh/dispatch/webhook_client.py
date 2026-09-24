import hmac
import hashlib
import json
from typing import Dict, Any, Optional

class WebhookDispatcher:
    """
    HTTP Webhook dispatcher with HMAC-SHA256 signing and exponential backoff.
    """
    @staticmethod
    def compute_signature(payload: Dict[str, Any], secret: str) -> str:
        raise NotImplementedError("To be implemented by Jules")

    @staticmethod
    def verify_signature(payload: Dict[str, Any], secret: str, signature_header: str) -> bool:
        raise NotImplementedError("To be implemented by Jules")

    @staticmethod
    def calculate_backoff(attempt: int, base_delay: float = 1.0, max_delay: float = 60.0) -> float:
        raise NotImplementedError("To be implemented by Jules")

    async def dispatch(self, url: str, payload: Dict[str, Any], secret: Optional[str] = None, max_retries: int = 3) -> bool:
        raise NotImplementedError("To be implemented by Jules")
