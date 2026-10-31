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
TITLE_COLUMN = "title"
CREATED_COLUMN = "created_at"

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


# ---------- CREATE / READ ----------
def create_chat(title: str):
    """Nayi chat banata hai aur uski id return karta hai."""
    res = _db().table(CHATS_TABLE).insert({TITLE_COLUMN: title}).execute()
    return res.data[0][ID_COLUMN]


def get_chats() -> list:
    """Saari chats, nayi se purani."""
    res = (
        _db().table(CHATS_TABLE)
        .select("*")
        .order(CREATED_COLUMN, desc=True)
        .execute()
    )
    return res.data or []


def save_message(chat_id, role: str, content: str) -> None:
    _db().table(MESSAGES_TABLE).insert(
        {MESSAGE_CHAT_COLUMN: chat_id, "role": role, "content": content}
    ).execute()


def get_messages(chat_id) -> list:
    res = (
        _db().table(MESSAGES_TABLE)
        .select("*")
        .eq(MESSAGE_CHAT_COLUMN, chat_id)
        .order(CREATED_COLUMN, desc=False)
        .execute()
    )
    return res.data or []


def count_messages(chat_id) -> int:
    res = (
        _db().table(MESSAGES_TABLE)
        .select(ID_COLUMN, count="exact")
        .eq(MESSAGE_CHAT_COLUMN, chat_id)
        .execute()
    )
    return res.count or 0


# ---------- UPDATE ----------
def rename_chat(chat_id, new_title: str) -> None:
    _db().table(CHATS_TABLE).update({TITLE_COLUMN: new_title}).eq(ID_COLUMN, chat_id).execute()


# ---------- DELETE ----------
def delete_chat(chat_id) -> None:
    """Ek chat aur us ke saare messages delete karta hai."""
    db = _db()
    db.table(MESSAGES_TABLE).delete().eq(MESSAGE_CHAT_COLUMN, chat_id).execute()
    db.table(CHATS_TABLE).delete().eq(ID_COLUMN, chat_id).execute()
    logger.info(f"Deleted chat {chat_id}")


def delete_all_chats() -> int:
    """Saari chats aur messages delete karta hai. Kitni chats delete hui woh return karta hai."""
    db = _db()
    rows = db.table(CHATS_TABLE).select(ID_COLUMN).execute().data or []
    ids = [r[ID_COLUMN] for r in rows]
    if not ids:
        return 0
    db.table(MESSAGES_TABLE).delete().in_(MESSAGE_CHAT_COLUMN, ids).execute()
    db.table(CHATS_TABLE).delete().in_(ID_COLUMN, ids).execute()
    logger.info(f"Deleted {len(ids)} chats")
    return len(ids)