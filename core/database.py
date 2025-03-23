import sqlite3
import numpy as np

class Database:
    """Управление базой данных для хранения описаний и эмбеддингов."""
    
    def __init__(self, db_path):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Инициализация таблицы в базе данных."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS entries (
                    path TEXT PRIMARY KEY,
                    description TEXT,
                    embedding BLOB,
                    extra TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_path ON entries(path)")
            conn.commit()
    
    def add_entry(self, path, description, embedding, extra=None):
        """Добавление записи в базу данных."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO entries (path, description, embedding, extra) VALUES (?, ?, ?, ?)",
                (path, description, embedding.tobytes(), extra)
            )
            conn.commit()
    
    def get_entry(self, path):
        """Получение записи по пути."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT description, embedding, extra FROM entries WHERE path = ?", (path,))
            result = cursor.fetchone()
            if result:
                desc, emb_bytes, extra = result
                embedding = np.frombuffer(emb_bytes, dtype=np.float32)
                return desc, embedding, extra
            return None, None, None
    
    def search(self, query_embedding, top_k=5):
        """Поиск по эмбеддингу с возвратом топ-N результатов."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT path, description, embedding, extra FROM entries")
            results = []
            for path, desc, emb_bytes, extra in cursor.fetchall():
                emb = np.frombuffer(emb_bytes, dtype=np.float32)
                similarity = np.dot(query_embedding, emb) / (np.linalg.norm(query_embedding) * np.linalg.norm(emb))
                results.append((path, desc, similarity, extra))
            return sorted(results, key=lambda x: x[2], reverse=True)[:top_k]