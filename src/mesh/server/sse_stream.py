import json
from typing import Dict, Any, Optional
from mesh.core.models import Event

class SSEEventFormatter:
    """
    Formats events into text/event-stream Server-Sent Events protocol format.
    """
    @staticmethod
    def format_event(event: Event) -> str:
        lines = []
        if event.id:
            lines.append(f"id: {event.id}")
        if event.topic:
            lines.append(f"event: {event.topic}")
        lines.append(f"data: {json.dumps(event.payload)}")
        return "\n".join(lines) + "\n\n"

    @staticmethod
    def format_raw(event_type: str, data: Dict[str, Any], event_id: Optional[str] = None) -> str:
        lines = []
        if event_id:
            lines.append(f"id: {event_id}")
        if event_type:
            lines.append(f"event: {event_type}")
        lines.append(f"data: {json.dumps(data)}")
        return "\n".join(lines) + "\n\n"
