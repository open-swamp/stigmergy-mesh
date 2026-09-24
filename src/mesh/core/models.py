from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional
import time
import json
import uuid

@dataclass
class Task:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    queue: str = "default"
    payload: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0  # Higher value = higher priority
    status: str = "pending"  # pending, active, completed, failed
    attempts: int = 0
    max_attempts: int = 3
    run_at: float = field(default_factory=time.time)
    lease_until: float = 0.0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        payload = data.get("payload", {})
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                payload = {}
        data_copy = dict(data)
        data_copy["payload"] = payload
        return cls(**data_copy)

@dataclass
class Event:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    topic: str = "general"
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    producer: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        payload = data.get("payload", {})
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                payload = {}
        data_copy = dict(data)
        data_copy["payload"] = payload
        return cls(**data_copy)

@dataclass
class DeadLetterEntry:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str = ""
    queue: str = "default"
    payload: Dict[str, Any] = field(default_factory=dict)
    reason: str = "max_retries_exceeded"
    failed_at: float = field(default_factory=time.time)
    attempts: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DeadLetterEntry":
        payload = data.get("payload", {})
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                payload = {}
        data_copy = dict(data)
        data_copy["payload"] = payload
        return cls(**data_copy)
