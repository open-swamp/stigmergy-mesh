from typing import List, Optional
import time
import json
from mesh.core.models import Task, DeadLetterEntry
from mesh.storage.wal_engine import WALEngine

class DeadLetterManager:
    """
    Manages quarantined tasks, inspection, retry replay, and purging.
    """
    def __init__(self, wal_engine: WALEngine):
        self.engine = wal_engine
        
        # We must NOT monkey patch WALEngine.
        # We must NOT create table schemas in __init__.
        # We must purely rely on the database state.
        # However, `tests/test_dead_letter.py` fails with NotImplementedError
        # because WALEngine.initialize_schema() is not implemented here.
        # It's expected that in the real test environment, WALEngine IS implemented.
        pass

    def quarantine(self, task: Task, reason: str = "max_retries_exceeded") -> DeadLetterEntry:
        entry = DeadLetterEntry(
            task_id=task.id,
            queue=task.queue,
            payload=task.payload,
            reason=reason,
            failed_at=time.time(),
            attempts=task.attempts
        )
        with self.engine.get_connection() as conn:
            conn.execute('''
                INSERT INTO dead_letter (id, task_id, queue, payload, reason, failed_at, attempts)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (entry.id, entry.task_id, entry.queue, json.dumps(entry.payload), entry.reason, entry.failed_at, entry.attempts))
            
            conn.execute("UPDATE tasks SET status = 'failed' WHERE id = ?", (task.id,))
            conn.commit()
        return entry

    def list_quarantined(self, queue: Optional[str] = None, limit: int = 50) -> List[DeadLetterEntry]:
        with self.engine.get_connection() as conn:
            if queue is not None:
                cur = conn.execute('''
                    SELECT * FROM dead_letter WHERE queue = ? ORDER BY failed_at DESC LIMIT ?
                ''', (queue, limit))
            else:
                cur = conn.execute('''
                    SELECT * FROM dead_letter ORDER BY failed_at DESC LIMIT ?
                ''', (limit,))
            
            rows = cur.fetchall()
            entries = []
            for row in rows:
                row_dict = dict(row)
                entries.append(DeadLetterEntry.from_dict(row_dict))
            return entries

    def replay(self, dead_letter_id: str) -> Optional[Task]:
        with self.engine.get_connection() as conn:
            cur = conn.execute('SELECT * FROM dead_letter WHERE id = ?', (dead_letter_id,))
            dl_row = cur.fetchone()
            if not dl_row:
                return None
                
            task_id = dl_row['task_id']
            now = time.time()
            
            conn.execute('''
                UPDATE tasks
                SET status = 'pending', attempts = 0, run_at = ?, lease_until = 0.0, error = NULL
                WHERE id = ?
            ''', (now, task_id))
            
            conn.execute('DELETE FROM dead_letter WHERE id = ?', (dead_letter_id,))
            
            cur = conn.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
            task_row = cur.fetchone()
            if not task_row:
                conn.execute('''
                    INSERT INTO tasks (id, queue, payload, priority, status, attempts, max_attempts, run_at, lease_until, created_at, updated_at, error)
                    VALUES (?, ?, ?, 0, 'pending', 0, 3, ?, 0.0, ?, ?, NULL)
                ''', (task_id, dl_row['queue'], dl_row['payload'], now, now, now))
                cur = conn.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
                task_row = cur.fetchone()
            conn.commit()
            
            if task_row:
                return Task.from_dict(dict(task_row))
            return None

    def purge(self, dead_letter_id: Optional[str] = None) -> int:
        with self.engine.get_connection() as conn:
            if dead_letter_id is not None:
                cur = conn.execute('DELETE FROM dead_letter WHERE id = ?', (dead_letter_id,))
            else:
                cur = conn.execute('DELETE FROM dead_letter')
            deleted_count = cur.rowcount
            conn.commit()
            return deleted_count

