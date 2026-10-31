import importlib
import html
import logging
import os
import uuid
import streamlit as st
import src.loader as document_loader

if not hasattr(document_loader, "load_file"):
    document_loader = importlib.reload(document_loader)

load_file = document_loader.load_file
from src.chunker import split_code_documents
from src.index_manifest import (
    build_upload_signature,
    load_index_manifest,
    save_index_manifest,
)
from src.vectorstore import create_vector_store, make_collection_name
from src.rag_pipeline import get_rag_chain
from src.database import (
    authenticate_user,
    create_user,
    create_chat,
    get_chats,
    save_message,
    get_messages,
    delete_chat,
)

# --- 1. CONSOLE LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

APP_NAME = "SourceLens"
APP_TAGLINE = "Ask questions. Get answers grounded in your files."

BRAND_SVG = (
    '<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">'
    '<path d="M8 4.75h10l6 6v8.5" stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>'
    '<path d="M18 4.75v6h6M8 4.75v22.5h8" stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>'
    '<path d="M11.5 15h7M11.5 19h4.5" stroke="white" stroke-width="1.6" stroke-linecap="round"/>'
    '<circle cx="22" cy="21" r="4.25" stroke="white" stroke-width="1.8"/>'
    '<path d="m25.1 24.1 3.15 3.15" stroke="white" stroke-width="2" stroke-linecap="round"/>'
    '</svg>'
)

# --- 2. PAGE CONFIG ---
st.set_page_config(
    page_title=f"{APP_NAME} | Local Code & Document RAG Assistant",
    page_icon="🔭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 3. STYLING ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
    --page: #F8F9FC;
    --panel: #FFFFFF;
    --raised: #EEF1F8;
    --line: #E2E7F0;
    --text: #111827;
    --muted: #4B5563;
    --accent: #4F5BD5;
    --accent-soft: rgba(79, 91, 213, 0.08);
    --ok: #10B981;
    --danger: #DC2626;
}

.stApp { background: var(--page); color: var(--text); font-family: 'Manrope', sans-serif; }
h1, h2, h3, button, input, textarea { font-family: 'Manrope', sans-serif !important; }

#MainMenu, footer, .stDeployButton, [data-testid="stAppDeployButton"] { display: none !important; }
header[data-testid="stHeader"] { background: transparent; }

.block-container { max-width: 960px; padding-top: 1.2rem; padding-bottom: 6rem; }

/* ---------- Brand ---------- */
.brand { display: flex; align-items: center; gap: 0.75rem; }
.brand-mark {
    width: 38px; height: 38px; border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    background: linear-gradient(135deg, #4F5BD5, #7C83F0); color: #FFFFFF;
    box-shadow: 0 4px 10px rgba(79, 91, 213, 0.2);
}
.brand-mark svg { width: 25px; height: 25px; }
.brand-name { font-weight: 700; font-size: 1.05rem; color: var(--text); line-height: 1.2; }
.brand-sub { font-size: 0.8rem; color: var(--muted); }

/* ---------- Navbar ---------- */
.st-key-navbar {
    background: var(--panel); border: 1px solid var(--line); border-radius: 16px;
    padding: 0.55rem 0.9rem; margin-bottom: 1.4rem;
    box-shadow: 0 4px 14px rgba(17, 24, 39, 0.05);
}
.st-key-navbar [data-testid="stHorizontalBlock"] { align-items: center; }
.st-key-navbar [data-testid="stBaseButton-primary"] {
    background: var(--accent); color: #FFFFFF; border: none;
    font-weight: 600; box-shadow: 0 3px 10px rgba(79, 91, 213, 0.25);
}
.st-key-navbar [data-testid="stBaseButton-primary"]:hover { background: #4049B8; }
.st-key-navbar [data-testid="stPopover"] button {
    background: var(--accent-soft); color: var(--accent);
    border: 1px solid rgba(79, 91, 213, 0.28); font-weight: 600;
}

/* ---------- Sidebar ---------- */
[data-testid="stSidebar"] { background: var(--panel); border-right: 1px solid var(--line); }
[data-testid="stSidebar"] .block-container { padding-top: 1.5rem; }

.side-section {
    margin: 0.2rem 0 0.5rem 0; color: var(--muted); font-size: 0.72rem;
    font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase;
}
.side-section.spaced { margin-top: 1.4rem; }
.side-help { font-size: 0.82rem; color: var(--muted); margin-bottom: 0.7rem; line-height: 1.5; }
.side-note { font-size: 0.8rem; color: var(--muted); line-height: 1.55; margin-top: 1.4rem;
    padding-top: 1rem; border-top: 1px solid var(--line); }
[data-testid="stFileUploaderDropzoneInstructions"] { display: none !important; }
[data-testid="stFileUploaderDropzone"] { justify-content: center !important; }

.indexed-files { margin-top: 0.7rem; }
.indexed-files-title {
    margin-bottom: 0.4rem; color: var(--muted); font-size: 0.72rem;
    font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase;
}
.indexed-file {
    display: flex; align-items: flex-start; gap: 0.5rem;
    padding: 0.5rem 0.6rem; margin-top: 0.35rem;
    border: 1px solid var(--line); border-radius: 9px;
    background: #FFFFFF; color: var(--text); font-size: 0.8rem;
    line-height: 1.45; overflow-wrap: anywhere;
}
.indexed-file-icon { flex: 0 0 auto; color: var(--accent); }
.indexed-file-icon svg { display: block; width: 1rem; height: 1rem; }

.guest-note {
    margin: 0.2rem 0 0.8rem 0; padding: 0.65rem 0.8rem;
    border: 1px dashed rgba(79, 91, 213, 0.4); border-radius: 10px;
    background: var(--accent-soft); color: #3730A3;
    font-size: 0.8rem; line-height: 1.5;
}

.confirm-box {
    background: #F3F4F6; border: 1px solid #E5E7EB; border-radius: 10px;
    padding: 0.7rem 0.8rem; font-size: 0.82rem; color: #374151; margin: 0.3rem 0 0.4rem 0;
}
.confirm-title { font-weight: 700; color: #1F2937; }
.confirm-detail { margin-top: 0.2rem; color: #6B7280; line-height: 1.45; }
[data-testid="stSidebar"] div[class*="st-key-yes_"] button {
    background: #B42318 !important; border-color: #B42318 !important;
    color: #FFFFFF !important; font-weight: 600 !important;
}
[data-testid="stSidebar"] div[class*="st-key-yes_"] button:hover {
    background: #912018 !important; border-color: #912018 !important;
}

/* ---------- Main ---------- */
.active-context-banner {
    display: flex; align-items: center; justify-content: space-between;
    padding: 0.6rem 1rem; background: var(--panel); border: 1px solid var(--line);
    border-radius: 8px; margin-bottom: 1.5rem; font-size: 0.88rem; box-shadow: 0 1px 2px rgba(0,0,0,0.02);
}
.active-context-left { display: flex; align-items: center; gap: 0.5rem; color: var(--muted); }
.active-context-path { font-family: 'JetBrains Mono', monospace; font-weight: 600; color: var(--text); }

div.hero h1 {
    font-size: 2rem; font-weight: 700; letter-spacing: -0.02em;
    line-height: 1.15; color: var(--text); margin: 0 0 0.5rem 0; padding: 0;
}
div.hero p { font-size: 0.98rem; color: var(--muted); line-height: 1.6; max-width: 65ch; margin: 0 0 1.2rem 0; }

.empty-title { font-weight: 600; font-size: 1.05rem; margin: 2rem 0 0.8rem 0; color: var(--text); }

[data-testid="stChatMessage"] {
    gap: 0.85rem; padding: 1.1rem 1.25rem; margin: 0.85rem 0;
    border: 1px solid var(--line); border-radius: 18px;
    background: var(--panel) !important;
    box-shadow: 0 4px 14px rgba(17, 24, 39, 0.045);
    transition: border-color 160ms ease, box-shadow 160ms ease;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
    flex-direction: row-reverse; width: fit-content;
    max-width: min(82%, 54rem); margin-left: auto;
    border-color: #E5E7EB; background: #F1F3F5 !important;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"])
    [data-testid="stChatMessageContent"] { text-align: left; }
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) { border-color: #E1E7F2; }
[data-testid="stChatMessage"]:hover { border-color: #CBD5E5; box-shadow: 0 7px 20px rgba(17, 24, 39, 0.07); }
[data-testid="stChatMessageAvatarCustom"] {
    width: 2.35rem; height: 2.35rem; flex: 0 0 2.35rem;
    border: 1px solid rgba(79, 91, 213, 0.16); border-radius: 12px !important;
    background: #FFFFFF; box-shadow: 0 2px 6px rgba(17, 24, 39, 0.07);
}
[data-testid="stChatMessageContent"] { min-width: 0; color: var(--text); line-height: 1.7; overflow-wrap: anywhere; }
[data-testid="stChatMessageContent"] p { margin-bottom: 0.75rem; }
[data-testid="stChatMessageContent"] p:last-child { margin-bottom: 0; }
[data-testid="stChatMessageContent"] pre { border: 1px solid var(--line); border-radius: 12px; }
[data-testid="stChatMessageContent"] table { border-collapse: collapse; }
[data-testid="stChatMessageContent"] th, [data-testid="stChatMessageContent"] td { padding: 0.55rem 0.7rem; border: 1px solid var(--line); }

[data-testid="stChatInput"] {
    border: 1px solid #D7DEEB; border-radius: 16px;
    background: var(--panel); box-shadow: 0 5px 18px rgba(17, 24, 39, 0.06);
}
[data-testid="stChatInput"] > div { align-items: center !important; padding: 6px 12px !important; }
[data-testid="stChatInput"] textarea { align-self: center !important; padding: 3px 0 !important; line-height: 1.45 !important; }
[data-testid="stChatInput"]:focus-within { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(79, 91, 213, 0.12); }

@media (max-width: 640px) {
    .block-container { padding: 1rem 1rem 5.5rem !important; }
    .brand-sub { display: none; }
    div.hero h1 { font-size: 1.65rem; line-height: 1.2; }
    .st-key-navbar [data-testid="stHorizontalBlock"] {
        flex-direction: row !important; flex-wrap: nowrap !important; gap: 0.5rem !important;
    }
    .st-key-navbar [data-testid="stHorizontalBlock"] > [data-testid="column"] {
        width: auto !important; min-width: 0 !important;
    }
}
</style>
""", unsafe_allow_html=True)

# --- 4. SESSION STATE ---
st.session_state.setdefault("user", None)
st.session_state.setdefault("guest_id", uuid.uuid4().hex[:12])
st.session_state.setdefault("guest_chats", [])
st.session_state.setdefault("guest_notice_shown", False)
st.session_state.setdefault("guest_reply_notice", False)
st.session_state.setdefault("active_collection", None)
st.session_state.setdefault("messages", [])
st.session_state.setdefault("quick_prompt", None)
st.session_state.setdefault("active_source_name", None)
st.session_state.setdefault("chunk_count", None)
st.session_state.setdefault("current_chat_id", None)
st.session_state.setdefault("pending_delete", None)
st.session_state.setdefault("upload_notice_signature", None)
st.session_state.setdefault("upload_widget_generation", 0)

user = st.session_state["user"]
owner_id = str(user["id"]) if user else st.session_state["guest_id"]
owner_upload_dir = os.path.join("data", "user_uploads", owner_id)
manifest_path = os.path.join(owner_upload_dir, ".indexed_manifest.json")
owner_changed = st.session_state.get("indexed_owner_id") != owner_id
if owner_changed:
    st.session_state["indexed_owner_id"] = owner_id
    st.session_state["active_file_key"] = None
    st.session_state["active_collection"] = None
    st.session_state["current_chat_id"] = None
    st.session_state["messages"] = []

index_manifest = load_index_manifest(manifest_path)
indexed_items = index_manifest.get("items", [])
if not isinstance(indexed_items, list):
    indexed_items = []
legacy_index_needs_rebuild = not indexed_items and bool(index_manifest.get("files"))
if owner_changed and indexed_items:
    st.session_state["active_file_key"] = indexed_items[-1].get("key")


def reset_active_view():
    st.session_state["messages"] = []
    st.session_state["current_chat_id"] = None
    st.session_state["active_source_name"] = None
    st.session_state["chunk_count"] = None


# --- 5. CHAT STORAGE (guest = session only, logged in = Supabase) ---
def store_create_chat(title: str):
    if user:
        return create_chat(user["id"], title)
    chat_id = f"guest-{uuid.uuid4().hex[:8]}"
    st.session_state["guest_chats"].append({"id": chat_id, "title": title, "messages": []})
    return chat_id


def store_save_message(chat_id, role: str, content: str):
    if user:
        save_message(chat_id, role, content)
        return
    for chat in st.session_state["guest_chats"]:
        if chat["id"] == chat_id:
            chat["messages"].append({"role": role, "content": content})
            return


def store_get_chats() -> list:
    if user:
        return get_chats(user["id"])
    return list(reversed(st.session_state["guest_chats"]))


def store_get_messages(chat_id) -> list:
    if user:
        return get_messages(chat_id)
    for chat in st.session_state["guest_chats"]:
        if chat["id"] == chat_id:
            return chat["messages"]
    return []


def activate_indexed_file(item: dict) -> None:
    st.session_state["active_file_key"] = item["key"]
    st.session_state["active_collection"] = item["collection"]
    st.session_state["active_source_name"] = item["name"]
    st.session_state["chunk_count"] = item["chunk_count"]
    st.session_state["current_chat_id"] = item["chat_id"]
    st.session_state["messages"] = [
        {"role": message["role"], "content": message["content"]}
        for message in store_get_messages(item["chat_id"])
    ]


active_file_item = next(
    (
        item for item in indexed_items
        if item.get("key") == st.session_state.get("active_file_key")
    ),
    None,
)
if active_file_item:
    st.session_state["active_collection"] = active_file_item["collection"]
    st.session_state["active_source_name"] = active_file_item["name"]
    st.session_state["chunk_count"] = active_file_item["chunk_count"]
    if st.session_state["current_chat_id"] != active_file_item["chat_id"]:
        activate_indexed_file(active_file_item)
else:
    st.session_state["active_collection"] = None


def store_delete_chat(chat_id):
    if user:
        delete_chat(chat_id, user["id"])
    else:
        st.session_state["guest_chats"] = [
            c for c in st.session_state["guest_chats"] if c["id"] != chat_id
        ]


def migrate_guest_chats(new_user_id) -> int:
    """Login ke baad guest session ki chats account mein save kar deta hai."""
    id_map = {}
    for chat in st.session_state["guest_chats"]:
        new_id = create_chat(new_user_id, chat["title"])
        for m in chat["messages"]:
            save_message(new_id, m["role"], m["content"])
        id_map[chat["id"]] = new_id

    current = st.session_state.get("current_chat_id")
    if current in id_map:
        st.session_state["current_chat_id"] = id_map[current]
    st.session_state["guest_chats"] = []
    return len(id_map)


def complete_login(logged_in_user: dict):
    st.session_state["user"] = logged_in_user
    saved = 0
    try:
        saved = migrate_guest_chats(logged_in_user["id"])
    except Exception as e:
        logger.error(f"Guest chat migration failed: {e}", exc_info=True)
    message = "Welcome to SourceLens!"
    if saved:
        message += f" {saved} chat(s) saved to your account."
    st.session_state["login_toast"] = message
    st.rerun()


# --- 6. AUTHENTICATION DIALOG ---
@st.dialog("Welcome to SourceLens")
def auth_dialog():
    login_tab, signup_tab = st.tabs(["Log in", "Create account"])
    with login_tab:
        st.caption("Log in to access your saved chat history.")
        with st.form("login_form"):
            login_email = st.text_input("Email", placeholder="you@example.com", key="login_email")
            login_password = st.text_input(
                "Password", type="password", placeholder="Your password", key="login_password"
            )
            login_submitted = st.form_submit_button(
                "Log in", type="primary", use_container_width=True
            )
        if login_submitted:
            if not login_email.strip() or not login_password:
                st.error("Please enter your email and password.")
            else:
                try:
                    found = authenticate_user(login_email, login_password)
                except Exception as e:
                    logger.error(f"Login failed: {e}", exc_info=True)
                    st.error("Could not reach the database. Please try again.")
                else:
                    if found:
                        complete_login(found)
                    else:
                        st.error("Invalid email or password.")

    with signup_tab:
        st.caption("Create an account to save and revisit your conversations.")
        with st.form("signup_form"):
            signup_email = st.text_input(
                "Email", placeholder="you@example.com", key="signup_email"
            )
            signup_password = st.text_input(
                "Password", type="password", placeholder="At least 6 characters",
                key="signup_password",
            )
            confirm_password = st.text_input(
                "Confirm password", type="password", placeholder="Enter your password again",
                key="signup_confirm_password",
            )
            signup_submitted = st.form_submit_button(
                "Create account", type="primary", use_container_width=True
            )
        if signup_submitted:
            if signup_password != confirm_password:
                st.error("Passwords do not match.")
            else:
                try:
                    new_user = create_user(signup_email, signup_password)
                except ValueError as e:
                    st.error(str(e))
                except Exception as e:
                    logger.error(f"Signup failed: {e}", exc_info=True)
                    st.error("Could not create your account. Please try again.")
                else:
                    complete_login(new_user)


# --- 7. TOASTS ---
login_toast = st.session_state.pop("login_toast", None)
if login_toast:
    st.toast(login_toast, icon=":material/check_circle:", duration=6)

if not user and not st.session_state["guest_notice_shown"]:
    st.toast("Log in to save your chat history.", icon=":material/info:", duration=8)
    st.session_state["guest_notice_shown"] = True


# --- 8. NAVBAR (logo + name on the left, login on the right) ---
def render_navbar():
    with st.container(key="navbar"):
        c_brand, c_action = st.columns([4, 1.7])
        c_brand.markdown(
            f'<div class="brand"><div class="brand-mark" aria-hidden="true">{BRAND_SVG}</div>'
            f'<div><div class="brand-name">{APP_NAME}</div>'
            f'<div class="brand-sub">Code & Document Assistant</div></div></div>',
            unsafe_allow_html=True,
        )
        with c_action:
            if user:
                email_initial = user["email"][:1]
                masked_email = f"{email_initial}••••••"
                with st.popover(
                    f":material/account_circle: {masked_email}",
                    use_container_width=True,
                ):
                    st.markdown("**Account**")
                    st.caption(masked_email)
                    if st.button(":material/logout: Log out", key="logout_btn", use_container_width=True):
                        st.session_state.clear()
                        st.rerun()
            else:
                if st.button(":material/login: Log in", key="nav_login",
                             type="primary", use_container_width=True):
                    auth_dialog()


render_navbar()

# --- 9. SIDEBAR: UPLOAD ---
st.sidebar.markdown(
    '<div class="side-section">Upload source</div>'
    '<div class="side-help">Upload code, PDF, or Excel files to get started.</div>',
    unsafe_allow_html=True
)
if legacy_index_needs_rebuild:
    st.sidebar.warning(
        "Your existing index combines files into one collection. Re-upload each "
        "file once to create separate file indexes and chats."
    )

uploaded_files = st.sidebar.file_uploader(
    "Upload code, PDF, or Excel files",
    key=f"source_upload_{st.session_state['upload_widget_generation']}",
    accept_multiple_files=True,
    type=[
        "py", "js", "ts", "tsx", "jsx", "json", "md", "html", "css", "pdf",
        "xlsx", "xlsm", "xls",
    ],
    label_visibility="collapsed"
)

uploaded_payloads = []
if uploaded_files:
    seen_uploads = set()
    seen_names = {}
    for uploaded_file in uploaded_files:
        file_name = os.path.basename(uploaded_file.name.replace("\\", "/"))
        original_name_key = file_name.casefold()
        content = uploaded_file.getvalue()
        signature = build_upload_signature([(file_name, content)])[0]
        identity = (original_name_key, signature["sha256"])
        if identity in seen_uploads:
            continue
        seen_uploads.add(identity)

        name_count = seen_names.get(original_name_key, 0)
        if name_count:
            stem, extension = os.path.splitext(file_name)
            file_name = f"{stem} ({name_count + 1}){extension}"
            signature = build_upload_signature([(file_name, content)])[0]
        seen_names[original_name_key] = name_count + 1
        uploaded_payloads.append({**signature, "content": content})

    upload_signature = tuple(
        (file_info["name"], file_info["key"])
        for file_info in sorted(
            uploaded_payloads,
            key=lambda item: (item["name"].casefold(), item["key"]),
        )
    )
    if upload_signature != st.session_state["upload_notice_signature"]:
        st.toast(
            f"{len(uploaded_payloads)} file(s) ready to index.",
            icon=":material/check_circle:",
            duration=5,
        )
        st.session_state["upload_notice_signature"] = upload_signature

    source_files_dir = os.path.join(owner_upload_dir, ".source_files")
    os.makedirs(source_files_dir, exist_ok=True)
    for payload in uploaded_payloads:
        extension = os.path.splitext(payload["name"])[1].lower()
        payload["path"] = os.path.join(
            source_files_dir, f"{payload['key']}{extension}"
        )
        with open(payload["path"], "wb") as source_file:
            source_file.write(payload["content"])
else:
    st.session_state["upload_notice_signature"] = None

index_button = False
if uploaded_payloads:
    index_button = st.sidebar.button(
        ":material/library_add: Index Files",
        type="primary",
        use_container_width=True,
    )

if index_button:
    with st.sidebar:
        manifest = load_index_manifest(manifest_path)
        indexed_items = manifest.get("items", [])
        indexed_count = 0
        skipped_count = 0
        failed_files = False

        with st.spinner("Processing files and building vector indexes..."):
            for payload in uploaded_payloads:
                existing_item = next(
                    (item for item in indexed_items if item.get("key") == payload["key"]),
                    None,
                )
                if existing_item:
                    activate_indexed_file(existing_item)
                    skipped_count += 1
                    continue

                try:
                    logger.info("Starting indexing for file: %s", payload["name"])
                    docs = load_file(payload["path"], payload["name"])
                    if not docs:
                        st.sidebar.error(f"No readable content found in {payload['name']}.")
                        failed_files = True
                        continue

                    chunks = split_code_documents(docs)
                    collection_name = make_collection_name(
                        payload["key"], user_id=owner_id
                    )
                    create_vector_store(
                        chunks, collection_name=collection_name, replace=True
                    )
                    previous_file = next(
                        (
                            item for item in indexed_items
                            if item.get("name", "").casefold()
                            == payload["name"].casefold()
                        ),
                        None,
                    )
                    chat_id = (
                        previous_file["chat_id"]
                        if previous_file
                        else store_create_chat(payload["name"])
                    )
                    item = {
                        "key": payload["key"],
                        "name": payload["name"],
                        "sha256": payload["sha256"],
                        "collection": collection_name,
                        "chat_id": chat_id,
                        "chunk_count": len(chunks),
                    }
                    indexed_items = [
                        previous for previous in indexed_items
                        if previous.get("name", "").casefold()
                        != payload["name"].casefold()
                    ]
                    indexed_items.append(item)
                    save_index_manifest(manifest_path, indexed_items)
                    activate_indexed_file(item)
                    indexed_count += 1
                except Exception as error:
                    st.sidebar.error(f"Indexing failed for {payload['name']}: {error}")
                    logger.exception("Indexing failed for %s", payload["name"])
                    failed_files = True

        if indexed_count:
            st.toast(
                f"Indexed {indexed_count} file(s) successfully.",
                icon=":material/task_alt:",
                duration=5,
            )
        if skipped_count:
            st.sidebar.info(
                f"{skipped_count} unchanged file(s) were already indexed."
            )
        if not failed_files:
            st.session_state["upload_widget_generation"] += 1
            st.session_state["upload_notice_signature"] = None
            st.rerun()
        if indexed_count:
            st.rerun()

if indexed_items:
    st.sidebar.markdown(
        '<div class="indexed-files-title">Indexed files</div>',
        unsafe_allow_html=True,
    )
    for item in indexed_items:
        is_active_file = item.get("key") == st.session_state.get("active_file_key")
        label = ("▶ " if is_active_file else "") + item["name"]
        if st.sidebar.button(
            label,
            key=f"activate_file_{item['key']}",
            help="Open this file's chat history and ask questions about this file.",
            use_container_width=True,
        ):
            activate_indexed_file(item)
            st.rerun()

# --- 10. SIDEBAR: HISTORY ---
st.sidebar.markdown('<div class="side-section spaced">History</div>', unsafe_allow_html=True)

if st.sidebar.button(":material/add: New Chat", use_container_width=True):
    reset_active_view()
    st.session_state["active_file_key"] = None
    st.session_state["active_collection"] = None
    st.session_state["pending_delete"] = None
    st.rerun()

if not user:
    st.sidebar.markdown(
        '<div class="guest-note"><b>Your chats are not saved.</b><br>'
        'Log in from the top right to keep your history.</div>',
        unsafe_allow_html=True,
    )

past_chats = []
try:
    past_chats = store_get_chats()
except Exception as e:
    logger.error(f"History load failed: {e}", exc_info=True)
    st.sidebar.warning("Could not load chat history.")

if past_chats:
    for chat in past_chats:
        cid = chat["id"]
        title = chat["title"]

        if st.session_state["pending_delete"] == cid:
            st.sidebar.markdown(
                f'<div class="confirm-box"><div class="confirm-title">Delete this chat?</div>'
                f'<div class="confirm-detail">{html.escape(title)} will be permanently deleted.</div></div>',
                unsafe_allow_html=True
            )
            c_yes, c_no = st.sidebar.columns(2)
            if c_yes.button(":material/delete: Delete", key=f"yes_{cid}",
                            type="primary", use_container_width=True):
                try:
                    store_delete_chat(cid)
                    deleted_file = next(
                        (
                            item for item in indexed_items
                            if str(item.get("chat_id")) == str(cid)
                        ),
                        None,
                    )
                    if deleted_file:
                        deleted_file["chat_id"] = store_create_chat(
                            deleted_file["name"]
                        )
                        save_index_manifest(manifest_path, indexed_items)
                    if st.session_state["current_chat_id"] == cid:
                        reset_active_view()
                    st.session_state["pending_delete"] = None
                    st.toast(f"Deleted '{title}'.", icon="🗑️")
                    st.rerun()
                except Exception as e:
                    st.sidebar.error(f"Delete failed: {e}")
                    logger.error(f"Delete failed: {e}", exc_info=True)
            if c_no.button("Cancel", key=f"no_{cid}", use_container_width=True):
                st.session_state["pending_delete"] = None
                st.rerun()
            continue

        is_active = st.session_state["current_chat_id"] == cid
        label = ("▶ " if is_active else "") + title
        col_chat, col_del = st.sidebar.columns([5, 1])
        if col_chat.button(label, key=f"open_{cid}", use_container_width=True):
            file_item = next(
                (
                    item for item in indexed_items
                    if str(item.get("chat_id")) == str(cid)
                ),
                None,
            )
            if file_item:
                activate_indexed_file(file_item)
            else:
                st.session_state["active_file_key"] = None
                st.session_state["active_collection"] = None
                st.session_state["current_chat_id"] = cid
                st.session_state["messages"] = [
                    {"role": m["role"], "content": m["content"]}
                    for m in store_get_messages(cid)
                ]
                st.session_state["active_source_name"] = title
                st.session_state["chunk_count"] = None
            st.rerun()
        if col_del.button(":material/delete_outline:", key=f"del_{cid}",
                          help="Delete this chat", use_container_width=True):
            st.session_state["pending_delete"] = cid
            st.rerun()
else:
    st.sidebar.info("No chats yet.")

st.sidebar.markdown(
    '<div class="side-note">Answers are grounded in the files you indexed.</div>',
    unsafe_allow_html=True
)

# --- 11. ACTIVE CONTEXT BANNER ---
if st.session_state["active_source_name"]:
    active_name = html.escape(str(st.session_state["active_source_name"]))
    chunk_count = st.session_state.get("chunk_count")
    chunk_info = f"{chunk_count} chunks indexed" if chunk_count else "Saved chat"
    st.markdown(
        f'<div class="active-context-banner">'
        f'<div class="active-context-left"><span>Active Context:</span> <span class="active-context-path">📄 {active_name}</span></div>'
        f'<div style="color: var(--muted); font-size: 0.8rem;">{chunk_info}</div>'
        f'</div>',
        unsafe_allow_html=True
    )

# --- 12. HERO ---
st.markdown(
    f'<div class="hero"><h1>{APP_TAGLINE}</h1>'
    f'<p>Upload code, PDFs, or documents. {APP_NAME} finds the relevant context '
    f'and answers using your files, with clear source references.</p></div>',
    unsafe_allow_html=True
)


# --- 13. CHAT INTERFACE ---
def render_chat_message(message):
    role = message["role"]
    avatar = ":material/person:" if role == "user" else ":material/smart_toy:"
    with st.chat_message(role, avatar=avatar):
        st.markdown(message["content"])


if not st.session_state.messages:
    st.markdown('<div class="empty-title">Try asking</div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("What files are indexed?", use_container_width=True):
            st.session_state.quick_prompt = "What are the main files or documents uploaded here?"
    with col2:
        if st.button("Summarize core logic", use_container_width=True):
            st.session_state.quick_prompt = "Summarize the core functionality or topics covered in these documents."
    with col3:
        if st.button("Test hallucination guardrail", use_container_width=True):
            st.session_state.quick_prompt = "Where is user authentication or database login implemented?"

for message in st.session_state.messages:
    render_chat_message(message)

prompt = st.chat_input("Ask about your uploaded files or code...")

if st.session_state.quick_prompt:
    prompt = st.session_state.quick_prompt
    st.session_state.quick_prompt = None

if prompt and not st.session_state.get("active_collection"):
    st.warning("Select an indexed file first to ask questions about its content.")
    prompt = None

if prompt:
    if not st.session_state.get("current_chat_id"):
        st.session_state["current_chat_id"] = store_create_chat("General Chat")

    st.session_state.messages.append({"role": "user", "content": prompt})
    store_save_message(st.session_state["current_chat_id"], "user", prompt)

    render_chat_message({"role": "user", "content": prompt})

    with st.chat_message("assistant", avatar=":material/smart_toy:"):
        with st.spinner("Analyzing documents..."):
            try:
                collection = st.session_state["active_collection"]
                chain, _ = get_rag_chain(collection)
                response = chain.invoke(prompt)
                st.markdown(response)

                st.session_state.messages.append({"role": "assistant", "content": response})
                store_save_message(st.session_state["current_chat_id"], "assistant", response)

                if not user and not st.session_state["guest_reply_notice"]:
                    st.toast("Log in to save your chat history.",
                             icon=":material/info:", duration=8)
                    st.session_state["guest_reply_notice"] = True
            except Exception as e:
                err_msg = f"**Error:** Index your files first, or check your API key.\n```text\n{e}\n```"
                st.markdown(err_msg)
                st.session_state.messages.append({"role": "assistant", "content": err_msg})