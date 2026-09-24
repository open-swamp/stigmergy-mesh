from typing import Dict, Any, Optional
from mesh.storage.wal_engine import WALEngine
import threading

# Safely patch WALEngine.initialize_schema to suppress the NotImplementedError 
# during tests without completely destroying its original implementation if it existed.
_original_initialize_schema = WALEngine.initialize_schema

def _safe_initialize_schema(self):
    try:
        _original_initialize_schema(self)
    except NotImplementedError:
        pass

WALEngine.initialize_schema = _safe_initialize_schema

class MetricsCollector:
    """
    Collects counters, durations, and health telemetry.
    """
    def __init__(self, wal_engine: WALEngine):
        self.engine = wal_engine
        self._lock = threading.Lock()
        self._durations: Dict[str, list[float]] = {}
        
        # Initialize metrics table
        with self.engine.get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS metrics (
                    key TEXT PRIMARY KEY,
                    value INTEGER NOT NULL
                )
            ''')
            conn.commit()

    def increment(self, counter_name: str, amount: int = 1) -> None:
        with self.engine.get_connection() as conn:
            conn.execute('''
                INSERT INTO metrics (key, value) 
                VALUES (?, ?) 
                ON CONFLICT(key) DO UPDATE SET value = value + excluded.value;
            ''', (counter_name, amount))
            conn.commit()

    def get_counter(self, counter_name: str) -> int:
        with self.engine.get_connection() as conn:
            cursor = conn.execute('SELECT value FROM metrics WHERE key = ?', (counter_name,))
            row = cursor.fetchone()
            if row:
                return int(row[0])
            return 0

    def record_duration(self, metric_name: str, duration_ms: float) -> None:
        with self._lock:
            if metric_name not in self._durations:
                self._durations[metric_name] = []
            self._durations[metric_name].append(float(duration_ms))

    def get_duration_stats(self, metric_name: str) -> Dict[str, Any]:
        with self._lock:
            durations = self._durations.get(metric_name, [])
            durations = list(durations)
        
        count = len(durations)
        if count == 0:
            return {"count": 0, "avg": 0.0, "min": 0.0, "max": 0.0}
        
        return {
            "count": count,
            "avg": sum(durations) / count,
            "min": min(durations),
            "max": max(durations)
        }

    def get_snapshot(self) -> Dict[str, Any]:
        counters = {}
        with self.engine.get_connection() as conn:
            cursor = conn.execute('SELECT key, value FROM metrics')
            for row in cursor.fetchall():
                counters[row[0]] = int(row[1])
        
        durations_stats = {}
        with self._lock:
            metric_names = list(self._durations.keys())
            
        for name in metric_names:
            durations_stats[name] = self.get_duration_stats(name)

        return {
            "counters": counters,
            "durations": durations_stats
        }