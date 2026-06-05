import sqlite3
from datetime import datetime

class ChatDatabase:
    def __init__(self, db_name="thread_history.db"):
        self.db_name = db_name
        self.create_tables()

    def get_connection(self):
        return sqlite3.connect(self.db_name)
    
    def create_tables(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS threads (
                    thread_id UUID PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()
    
    def save_thread(self, thread_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                'INSERT OR IGNORE INTO threads (thread_id) VALUES (?)',
                (str(thread_id),)
            )

            conn.commit()

    def get_threads(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                'SELECT * FROM threads'
            )

            return cursor.fetchall()