from typing import Dict, Any, Optional, List
from mesh.core.models import Task
from mesh.storage.wal_engine import WALEngine
import time
import json

_original_initialize_schema = WALEngine.initialize_schema

def _safe_initialize_schema(self) -> None:
    try:
        _original_initialize_schema(self)
    except NotImplementedError:
        pass
    with self.get_connection() as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                queue TEXT NOT NULL,
                payload TEXT NOT NULL,
                priority INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                attempts INTEGER DEFAULT 0,
                max_attempts INTEGER DEFAULT 3,
                run_at REAL NOT NULL,
                lease_until REAL DEFAULT 0.0,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                error TEXT
            )
        """)
        conn.commit()

WALEngine.initialize_schema = _safe_initialize_schema

class PriorityQueueManager:
    """
    Manages priority-based task queues with leases, delays, and retries.
    """
    def __init__(self, wal_engine: WALEngine):
        self.engine = wal_engine

    def push(self, queue: str, payload: Dict[str, Any], priority: int = 0, delay_seconds: float = 0.0, max_attempts: int = 3) -> Task:
        task = Task(
            queue=queue,
            payload=payload,
            priority=priority,
            max_attempts=max_attempts,
            run_at=time.time() + delay_seconds
        )
        with self.engine.get_connection() as conn:
            conn.execute(
                '''INSERT INTO tasks (id, queue, payload, priority, status, attempts, max_attempts, run_at, lease_until, created_at, updated_at, error)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (task.id, task.queue, json.dumps(task.payload), task.priority, task.status, task.attempts, task.max_attempts, task.run_at, task.lease_until, task.created_at, task.updated_at, task.error)
            )
            conn.commit()
        return task

    def pop(self, queue: str, lease_seconds: float = 30.0) -> Optional[Task]:
        now = time.time()
        lease_until = now + lease_seconds
        with self.engine.get_connection() as conn:
            cursor = conn.execute(
                '''UPDATE tasks 
                   SET status = 'active', lease_until = ?, updated_at = ? 
                   WHERE id = (
                       SELECT id FROM tasks 
                       WHERE queue = ? AND run_at <= ? AND (status = 'pending' OR (status = 'active' AND lease_until < ?))
                       ORDER BY priority DESC, run_at ASC LIMIT 1
                   )
                   RETURNING *''',
                (lease_until, now, queue, now, now)
            )
            row = cursor.fetchone()
            conn.commit()
            if row:
                return Task.from_dict(dict(row))
            return None

    def ack(self, task_id: str) -> bool:
        with self.engine.get_connection() as conn:
            cursor = conn.execute(
                '''UPDATE tasks 
                   SET status = 'completed', updated_at = ? 
                   WHERE id = ?''',
                (time.time(), task_id)
            )
            conn.commit()
            return cursor.rowcount > 0

    def nack(self, task_id: str, error: Optional[str] = None) -> bool:
        with self.engine.get_connection() as conn:
            cursor = conn.execute(
                '''UPDATE tasks 
                   SET status = 'pending', lease_until = 0.0, attempts = attempts + 1, error = ?, updated_at = ? 
                   WHERE id = ?''',
                (error, time.time(), task_id)
            )
            conn.commit()
            return cursor.rowcount > 0

    def peek(self, queue: str, limit: int = 10) -> List[Task]:
        with self.engine.get_connection() as conn:
            cursor = conn.execute(
                '''SELECT * FROM tasks 
                   WHERE queue = ? AND status = 'pending'
                   ORDER BY priority DESC, run_at ASC LIMIT ?''',
                (queue, limit)
            )
            return [Task.from_dict(dict(row)) for row in cursor.fetchall()]

    def stats(self, queue: Optional[str] = None) -> Dict[str, Any]:
        with self.engine.get_connection() as conn:
            if queue:
                cursor = conn.execute(
                    '''SELECT status, COUNT(*) as count FROM tasks 
                       WHERE queue = ? GROUP BY status''',
                    (queue,)
                )
            else:
                cursor = conn.execute(
                    '''SELECT status, COUNT(*) as count FROM tasks 
                       GROUP BY status'''
                )
            rows = cursor.fetchall()
            stats = {
                "pending": 0,
                "active": 0,
                "completed": 0,
                "failed": 0
            }
            for row in rows:
                stats[row['status']] = row['count']
            return stats
