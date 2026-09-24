import hmac
import hashlib
import json
import urllib.request
import urllib.error
import asyncio
from typing import Dict, Any, Optional

class WebhookDispatcher:
    """
    HTTP Webhook dispatcher with HMAC-SHA256 signing and exponential backoff.
    """
    @staticmethod
    def compute_signature(payload: Dict[str, Any], secret: str) -> str:
        raw_body = json.dumps(payload, sort_keys=True).encode("utf-8")
        digest = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
        return f"sha256={digest}"

    @staticmethod
    def verify_signature(payload: Dict[str, Any], secret: str, signature_header: str) -> bool:
        expected = WebhookDispatcher.compute_signature(payload, secret)
        return hmac.compare_digest(expected, signature_header)

    @staticmethod
    def calculate_backoff(attempt: int, base_delay: float = 1.0, max_delay: float = 60.0) -> float:
        return min(max_delay, base_delay * (2 ** attempt))

    async def dispatch(self, url: str, payload: Dict[str, Any], secret: Optional[str] = None, max_retries: int = 3) -> bool:
        data = json.dumps(payload).encode("utf-8")
        headers = {'Content-Type': 'application/json'}
        if secret:
            headers['X-Mesh-Signature'] = self.compute_signature(payload, secret)

        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        def _do_req():
            try:
                with urllib.request.urlopen(req) as response:
                    return response.status
            except urllib.error.HTTPError as e:
                return e.code
            except urllib.error.URLError:
                return None

        for attempt in range(max_retries + 1):
            status = await asyncio.to_thread(_do_req)
            
            if status is not None and 200 <= status < 300:
                return True
                
            if status is None or status >= 500:
                if attempt < max_retries:
                    delay = self.calculate_backoff(attempt)
                    await asyncio.sleep(delay)
            else:
                # E.g. 4xx, we don't retry
                return False
                
        return False
