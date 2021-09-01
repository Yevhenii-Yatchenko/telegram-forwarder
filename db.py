import os
import sqlite3
from typing import List, Tuple

from telebot.types import Message


conn = sqlite3.connect(os.path.join(os.path.dirname(__file__), "bot.db"))
cursor = conn.cursor()

SQL_INSERT_MESSAGE = """
INSERT INTO messages (sender_id, message)
              VALUES (?, ?)
"""

SQL_FETCH_SUBSCRIBERS = 'SELECT id FROM subscribers'

SQL_INSERT_SUBSCRIBER = """
INSERT OR REPLACE INTO subscribers (id, init_datetime)
                            VALUES (?, ?)
"""

SQL_DELETE_SUBSCRIBER = 'DELETE FROM subscribers WHERE id = ?'

SQL_INSERT_SENDER = """
INSERT OR REPLACE INTO senders (id, init_datetime)
                        VALUES (?, ?)
"""

SQL_FETCH_SENDERS = 'SELECT id FROM senders'

SQL_DELETE_SENDER = 'DELETE FROM senders WHERE id = ?'


def insert_message(message: Message):
    sender_id = str(message.from_user.id)

    cursor.execute(SQL_INSERT_MESSAGE, (sender_id, str(message.json)))
    conn.commit()


def insert_subscriber(id:str, init_datetime:str):
    cursor.execute(SQL_INSERT_SUBSCRIBER, (id, init_datetime))
    conn.commit()


def fetch_subscribers() -> List[Tuple]:
    cursor.execute(SQL_FETCH_SUBSCRIBERS)
    return cursor.fetchall()

def delete_subscriber(id: str):
    cursor.execute(SQL_DELETE_SUBSCRIBER, (id,))
    conn.commit()


def insert_sender(id:str, init_datetime:str):
    cursor.execute(SQL_INSERT_SENDER, (id, init_datetime))
    conn.commit()


def fetch_senders() -> List[Tuple]:
    cursor.execute(SQL_FETCH_SENDERS)
    return cursor.fetchall()


def delete_sender(id: str):
    cursor.execute(SQL_DELETE_SENDER, (id,))
    conn.commit()


def _init_db():
    init_db_path = os.path.join(os.path.dirname(__file__), "init_db.sql")
    with open(init_db_path, "r") as queries_file:
        sql = queries_file.read()
    cursor.executescript(sql)
    conn.commit()


_init_db()
