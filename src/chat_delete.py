import os
import logging
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
logger = logging.getLogger(__name__)

# --- Agar aap ke Supabase mein naam alag hain to yahan badlein ---
CHATS_TABLE = "chats"
MESSAGES_TABLE = "messages"
MESSAGE_CHAT_COLUMN = "chat_id"
ID_COLUMN = "id"

_client = None


def _db():
    global _client
    if _client is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            raise RuntimeError("SUPABASE_URL / SUPABASE_KEY .env mein nahi mile.")
        _client = create_client(url, key)
    return _client


def delete_chat(chat_id) -> None:
    """Ek chat aur us ke saare messages delete karta hai."""
    db = _db()
    db.table(MESSAGES_TABLE).delete().eq(MESSAGE_CHAT_COLUMN, chat_id).execute()
    db.table(CHATS_TABLE).delete().eq(ID_COLUMN, chat_id).execute()
    logger.info(f"Deleted chat {chat_id}")


def delete_all_chats() -> None:
    """Saari chats aur saare messages delete karta hai."""
    db = _db()
    rows = db.table(CHATS_TABLE).select(ID_COLUMN).execute().data or []
    ids = [r[ID_COLUMN] for r in rows]
    if not ids:
        return
    db.table(MESSAGES_TABLE).delete().in_(MESSAGE_CHAT_COLUMN, ids).execute()
    db.table(CHATS_TABLE).delete().in_(ID_COLUMN, ids).execute()
    logger.info(f"Deleted {len(ids)} chats")