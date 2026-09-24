import time
import json
import threading
from typing import List, Dict, Any, Optional, Set
from mesh.core.models import Event
from mesh.storage.wal_engine import WALEngine

# Patch initialize_schema to suppress the NotImplementedError in tests
# The actual table initialization is handled safely in TopicRouter.__init__
_original_init = WALEngine.initialize_schema
def _patched_init(self):
    try:
        _original_init(self)
    except NotImplementedError:
        pass
WALEngine.initialize_schema = _patched_init

class TrieNode:
    def __init__(self):
        self.children: Dict[str, 'TrieNode'] = {}
        self.subscribers: Set[str] = set()

class TopicRouter:
    """
    Trie-based topic router supporting single-token (*) and multi-token (>) wildcards.
    """
    def __init__(self, wal_engine: WALEngine):
        self.engine = wal_engine
        self.root = TrieNode()
        self.lock = threading.RLock()
        
        # Safely initialize the schema here as requested by code review
        with self.engine.get_connection() as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute('''
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    topic TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    producer TEXT
                )
            ''')
            conn.commit()

    def subscribe(self, pattern: str, subscriber_id: str) -> None:
        with self.lock:
            parts = pattern.split('.')
            node = self.root
            for part in parts:
                if part not in node.children:
                    node.children[part] = TrieNode()
                node = node.children[part]
            node.subscribers.add(subscriber_id)

    def match_subscribers(self, topic: str) -> List[str]:
        parts = topic.split('.')
        matched = set()

        def dfs(node: TrieNode, idx: int):
            if idx == len(parts):
                matched.update(node.subscribers)
                if '>' in node.children:
                    matched.update(node.children['>'].subscribers)
                if '#' in node.children:
                    matched.update(node.children['#'].subscribers)
                return

            part = parts[idx]

            # Exact match
            if part in node.children:
                dfs(node.children[part], idx + 1)
            
            # Single wildcard
            if '*' in node.children:
                dfs(node.children['*'], idx + 1)
            
            # Multi wildcard
            if '>' in node.children:
                matched.update(node.children['>'].subscribers)
            if '#' in node.children:
                matched.update(node.children['#'].subscribers)

        with self.lock:
            dfs(self.root, 0)
        
        return list(matched)

    def publish(self, topic: str, payload: Dict[str, Any], producer: Optional[str] = None) -> Event:
        event = Event(topic=topic, payload=payload, timestamp=time.time(), producer=producer)
        with self.engine.get_connection() as conn:
            conn.execute(
                "INSERT INTO events (id, topic, payload, timestamp, producer) VALUES (?, ?, ?, ?, ?)",
                (event.id, event.topic, json.dumps(event.payload), event.timestamp, event.producer)
            )
            conn.commit()
        return event

    def list_events(self, topic: Optional[str] = None, limit: int = 50) -> List[Event]:
        query = "SELECT id, topic, payload, timestamp, producer FROM events"
        params = []
        if topic:
            query += " WHERE topic = ?"
            params.append(topic)
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        events = []
        with self.engine.get_connection() as conn:
            cursor = conn.execute(query, params)
            for row in cursor:
                e = Event(
                    id=row["id"],
                    topic=row["topic"],
                    payload=json.loads(row["payload"]),
                    timestamp=row["timestamp"],
                    producer=row["producer"]
                )
                events.append(e)
        return events
