import unittest
import hmac
import hashlib
import json
from mesh.dispatch.webhook_client import WebhookDispatcher

class TestWebhookClient(unittest.TestCase):
    def test_signature_generation(self):
        secret = "secret-token-key-123"
        payload = {"event": "task.completed", "id": "t-99"}
        
        signature = WebhookDispatcher.compute_signature(payload, secret)
        self.assertIsNotNone(signature)
        
        # Verify correctness with HMAC-SHA256
        raw_body = json.dumps(payload, sort_keys=True).encode("utf-8")
        expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
        self.assertEqual(signature, f"sha256={expected}")

    def test_backoff_calculation(self):
        # Base: 1.0, factor: 2.0
        d0 = WebhookDispatcher.calculate_backoff(attempt=0, base_delay=1.0, max_delay=60.0)
        d1 = WebhookDispatcher.calculate_backoff(attempt=1, base_delay=1.0, max_delay=60.0)
        d2 = WebhookDispatcher.calculate_backoff(attempt=2, base_delay=1.0, max_delay=60.0)
        
        self.assertGreaterEqual(d0, 1.0)
        self.assertGreaterEqual(d1, 2.0)
        self.assertGreaterEqual(d2, 4.0)

    def test_verify_signature_validator(self):
        secret = "agent-secret"
        payload = {"status": "ok"}
        sig = WebhookDispatcher.compute_signature(payload, secret)
        
        is_valid = WebhookDispatcher.verify_signature(payload, secret, sig)
        self.assertTrue(is_valid)

        is_invalid = WebhookDispatcher.verify_signature(payload, "wrong-secret", sig)
        self.assertFalse(is_invalid)

if __name__ == "__main__":
    unittest.main()
