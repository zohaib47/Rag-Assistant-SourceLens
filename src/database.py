import hashlib
import hmac
import logging
import os
import re
import secrets
import sys
from functools import wraps
from typing import Callable, ParamSpec, TypeVar

import streamlit as st
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.propagate = False
if not any(
    getattr(handler, "_database_console_handler", False)
    for handler in logger.handlers
):
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    console_handler._database_console_handler = True
    logger.addHandler(console_handler)

P = ParamSpec("P")
R = TypeVar("R")


def _log_backend_errors(function: Callable[P, R]) -> Callable[P, R]:
    @wraps(function)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return function(*args, **kwargs)
        except Exception:
            logger.exception("Backend operation %s failed", function.__name__)
            raise

    return wrapped


# --- Table and Column Constants ---
USERS_TABLE = "users"
CHATS_TABLE = "chats"
MESSAGES_TABLE = "messages"

USER_ID_COLUMN = "id"
USER_EMAIL_COLUMN = "email"
USER_PASSWORD_COLUMN = "password"
CHAT_USER_ID_COLUMN = "user_id"
MESSAGE_CHAT_COLUMN = "chat_id"
ID_COLUMN = "id"
TITLE_COLUMN = "title"
CREATED_COLUMN = "created_at"
PASSWORD_HASH_PREFIX = "pbkdf2_sha256"
PASSWORD_HASH_ITERATIONS = 600_000

_client = None


@_log_backend_errors
def _db():
    global _client
    if _client is None:
        url = None
        key = None
        try:
            if hasattr(st, "secrets") and "SUPABASE_URL" in st.secrets:
                url = st.secrets["SUPABASE_URL"]
                key = st.secrets["SUPABASE_KEY"]
        except Exception as error:
            logger.info(
                "Streamlit secrets unavailable; trying environment variables (%s)",
                type(error).__name__,
            )

        if not url or not key:
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_KEY")

        if not url or not key:
            raise RuntimeError("SUPABASE_URL / SUPABASE_KEY .env ya Streamlit secrets mein nahi mile.")
        _client = create_client(url, key)
    return _client


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_HASH_ITERATIONS
    )
    return (
        f"{PASSWORD_HASH_PREFIX}${PASSWORD_HASH_ITERATIONS}"
        f"${salt.hex()}${digest.hex()}"
    )


def _verify_password(password: str, stored_password: str) -> tuple[bool, bool]:
    """Return (valid, needs_upgrade); legacy plaintext is upgraded after successful login."""
    if not stored_password.startswith(f"{PASSWORD_HASH_PREFIX}$"):
        return (
            hmac.compare_digest(password.encode("utf-8"), stored_password.encode("utf-8")),
            True,
        )

    try:
        algorithm, iterations_text, salt_hex, digest_hex = stored_password.split("$", 3)
        iterations = int(iterations_text)
        if algorithm != PASSWORD_HASH_PREFIX or not 100_000 <= iterations <= 1_000_000:
            return False, False
        salt = bytes.fromhex(salt_hex)
        expected_digest = bytes.fromhex(digest_hex)
    except (ValueError, TypeError):
        return False, False

    actual_digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iterations
    )
    return hmac.compare_digest(actual_digest, expected_digest), False


@_log_backend_errors
def authenticate_user(email: str, password: str) -> dict | None:
    """Authenticate against users table and upgrade legacy plaintext passwords."""
    normalized_email = email.strip().lower()
    if not normalized_email or not password:
        return None

    result = (
        _db().table(USERS_TABLE)
        .select(f"{USER_ID_COLUMN},{USER_EMAIL_COLUMN},{USER_PASSWORD_COLUMN}")
        .eq(USER_EMAIL_COLUMN, normalized_email)
        .limit(1)
        .execute()
    )
    if not result.data:
        logger.warning("Authentication failed: account not found")
        return None

    account = result.data[0]
    valid, needs_upgrade = _verify_password(password, account[USER_PASSWORD_COLUMN])
    if not valid:
        logger.warning("Authentication failed: invalid password")
        return None

    if needs_upgrade:
        _db().table(USERS_TABLE).update({
            USER_PASSWORD_COLUMN: _hash_password(password)
        }).eq(USER_ID_COLUMN, account[USER_ID_COLUMN]).execute()

    return {
        "id": str(account[USER_ID_COLUMN]),
        "name": normalized_email.partition("@")[0],
        "email": normalized_email,
    }


@_log_backend_errors
def create_user(email: str, password: str) -> dict:
    """Create an account in the custom users table with a salted password hash."""
    normalized_email = email.strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized_email):
        raise ValueError("Please enter a valid email address.")
    if len(password) < 6:
        raise ValueError("Password must be at least 6 characters long.")

    db = _db()
    existing = (
        db.table(USERS_TABLE)
        .select(USER_ID_COLUMN)
        .eq(USER_EMAIL_COLUMN, normalized_email)
        .limit(1)
        .execute()
    )
    if existing.data:
        raise ValueError("An account with this email already exists.")

    result = (
        db.table(USERS_TABLE)
        .insert({
            USER_EMAIL_COLUMN: normalized_email,
            USER_PASSWORD_COLUMN: _hash_password(password),
        })
        .execute()
    )
    if not result.data:
        raise RuntimeError("Account creation returned no user record.")

    account = result.data[0]
    return {
        "id": str(account[USER_ID_COLUMN]),
        "name": normalized_email.partition("@")[0],
        "email": normalized_email,
    }


# ---------- CREATE / READ CHATS ----------
@_log_backend_errors
def create_chat(user_id: str, title: str):
    """Create a chat owned by the specified user ID."""
    res = _db().table(CHATS_TABLE).insert({
        CHAT_USER_ID_COLUMN: user_id,
        TITLE_COLUMN: title
    }).execute()
    return res.data[0][ID_COLUMN]


@_log_backend_errors
def get_chats(user_id: str) -> list:
    """Fetch chats belonging to one user, newest first."""
    if not user_id:
        return []
    res = (
        _db().table(CHATS_TABLE)
        .select("*")
        .eq(CHAT_USER_ID_COLUMN, user_id)
        .order(CREATED_COLUMN, desc=True)
        .execute()
    )
    return res.data or []


@_log_backend_errors
def save_message(chat_id, role: str, content: str) -> None:
    _db().table(MESSAGES_TABLE).insert(
        {MESSAGE_CHAT_COLUMN: chat_id, "role": role, "content": content}
    ).execute()


@_log_backend_errors
def get_messages(chat_id) -> list:
    res = (
        _db().table(MESSAGES_TABLE)
        .select("*")
        .eq(MESSAGE_CHAT_COLUMN, chat_id)
        .order(CREATED_COLUMN, desc=False)
        .execute()
    )
    return res.data or []


@_log_backend_errors
def count_messages(chat_id) -> int:
    res = (
        _db().table(MESSAGES_TABLE)
        .select(ID_COLUMN, count="exact")
        .eq(MESSAGE_CHAT_COLUMN, chat_id)
        .execute()
    )
    return res.count or 0


# ---------- UPDATE ----------
@_log_backend_errors
def rename_chat(chat_id, new_title: str) -> None:
    _db().table(CHATS_TABLE).update({TITLE_COLUMN: new_title}).eq(ID_COLUMN, chat_id).execute()


# ---------- DELETE ----------
@_log_backend_errors
def delete_chat(chat_id, user_id: str | None = None) -> None:
    """Delete a chat and its messages, optionally restricting deletion to its owner."""
    db = _db()
    chat_query = db.table(CHATS_TABLE).select(ID_COLUMN).eq(ID_COLUMN, chat_id)
    if user_id is not None:
        chat_query = chat_query.eq(CHAT_USER_ID_COLUMN, user_id)
    if not chat_query.execute().data:
        return

    db.table(MESSAGES_TABLE).delete().eq(MESSAGE_CHAT_COLUMN, chat_id).execute()
    delete_query = db.table(CHATS_TABLE).delete().eq(ID_COLUMN, chat_id)
    if user_id is not None:
        delete_query = delete_query.eq(CHAT_USER_ID_COLUMN, user_id)
    delete_query.execute()
    logger.info(f"Deleted chat {chat_id}")
