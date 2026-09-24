import json
from typing import Dict, Any, Optional
from mesh.core.models import Event

class SSEEventFormatter:
    """
    Formats events into text/event-stream Server-Sent Events protocol format.
    """
    @staticmethod
    def format_event(event: Event) -> str:
        raise NotImplementedError("To be implemented by Jules")

    @staticmethod
    def format_raw(event_type: str, data: Dict[str, Any], event_id: Optional[str] = None) -> str:
        raise NotImplementedError("To be implemented by Jules")
