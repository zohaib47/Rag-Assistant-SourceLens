import html
import hashlib
import logging
import os
import streamlit as st
from src.loader import load_codebase
from src.chunker import split_code_documents
from src.vectorstore import create_vector_store
from src.rag_pipeline import get_rag_chain
from src.database import (
    create_chat, get_chats, save_message, get_messages,
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

.block-container { max-width: 960px; padding-top: 2rem; padding-bottom: 6rem; }

[data-testid="stSidebar"] { background: var(--panel); border-right: 1px solid var(--line); }
[data-testid="stSidebar"] .block-container { padding-top: 1.5rem; }

.brand { display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1.6rem; }
.brand-mark {
    width: 38px; height: 38px; border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    background: linear-gradient(135deg, #4F5BD5, #7C83F0); color: #FFFFFF;
    box-shadow: 0 4px 10px rgba(79, 91, 213, 0.2);
}
.brand-mark svg { width: 25px; height: 25px; }
.brand-name { font-weight: 700; font-size: 1.05rem; color: var(--text); line-height: 1.2; }
.brand-sub { font-size: 0.8rem; color: var(--muted); }

.side-title { font-weight: 600; font-size: 0.95rem; color: var(--text); margin: 0 0 0.2rem 0; }
.side-help { font-size: 0.82rem; color: var(--muted); margin-bottom: 0.9rem; line-height: 1.5; }
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

/* Clear, consistent chat message cards. */
[data-testid="stChatMessage"] {
    gap: 0.85rem;
    padding: 1.1rem 1.25rem;
    margin: 0.85rem 0;
    border: 1px solid var(--line);
    border-radius: 18px;
    background: var(--panel) !important;
    box-shadow: 0 4px 14px rgba(17, 24, 39, 0.045);
    transition: border-color 160ms ease, box-shadow 160ms ease;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
    flex-direction: row-reverse;
    width: fit-content;
    max-width: min(82%, 54rem);
    margin-left: auto;
    border-color: #E5E7EB;
    background: #F1F3F5 !important;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"])
    [data-testid="stChatMessageContent"] {
    text-align: left;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
    border-color: #E1E7F2;
}
[data-testid="stChatMessage"]:hover {
    border-color: #CBD5E5;
    box-shadow: 0 7px 20px rgba(17, 24, 39, 0.07);
}
[data-testid="stChatMessageAvatarCustom"] {
    width: 2.35rem;
    height: 2.35rem;
    flex: 0 0 2.35rem;
    border: 1px solid rgba(79, 91, 213, 0.16);
    border-radius: 12px !important;
    background: #FFFFFF;
    box-shadow: 0 2px 6px rgba(17, 24, 39, 0.07);
}
[data-testid="stChatMessageContent"] {
    min-width: 0;
    color: var(--text);
    line-height: 1.7;
    overflow-wrap: anywhere;
}
[data-testid="stChatMessageContent"] p {
    margin-bottom: 0.75rem;
}
[data-testid="stChatMessageContent"] p:last-child {
    margin-bottom: 0;
}
[data-testid="stChatMessageContent"] pre {
    border: 1px solid var(--line);
    border-radius: 12px;
}
[data-testid="stChatMessageContent"] table {
    border-collapse: collapse;
}
[data-testid="stChatMessageContent"] th,
[data-testid="stChatMessageContent"] td {
    padding: 0.55rem 0.7rem;
    border: 1px solid var(--line);
}

[data-testid="stChatInput"] {
    border: 1px solid #D7DEEB;
    border-radius: 16px;
    background: var(--panel);
    box-shadow: 0 5px 18px rgba(17, 24, 39, 0.06);
}
[data-testid="stChatInput"] > div {
    align-items: center !important;
    padding: 6px 12px !important;
}
[data-testid="stChatInput"] textarea {
    align-self: center !important;
    padding: 3px 0 !important;
    line-height: 1.45 !important;
}
[data-testid="stChatInput"]:focus-within {
    border-color: var(--accent);
    box-shadow: 0 0 0 3px rgba(79, 91, 213, 0.12);
}

@media (max-width: 640px) {
    .block-container {
        padding: 1.2rem 1rem 5.5rem !important;
    }
    [data-testid="stSidebar"] .block-container {
        padding: 1rem 0.9rem !important;
    }
    div.hero h1 {
        font-size: 1.65rem;
        line-height: 1.2;
    }
    div.hero p {
        font-size: 0.92rem;
        line-height: 1.55;
    }
    .active-context-banner {
        align-items: flex-start;
        flex-direction: column;
        gap: 0.35rem;
        margin-bottom: 1rem;
        overflow-wrap: anywhere;
    }
    .active-context-left {
        align-items: flex-start;
        flex-wrap: wrap;
    }
    [data-testid="stMain"] [data-testid="stHorizontalBlock"] {
        flex-direction: column;
        gap: 0.55rem;
    }
    [data-testid="stMain"] [data-testid="stHorizontalBlock"] > [data-testid="column"] {
        width: 100% !important;
        flex: 1 1 100% !important;
    }
    [data-testid="stMain"] [data-testid="stHorizontalBlock"] .stButton > button {
        width: 100%;
        min-height: 2.75rem;
        white-space: normal;
    }
    [data-testid="stChatMessage"] {
        gap: 0.6rem;
        padding: 0.8rem;
        margin: 0.65rem 0;
        border-radius: 14px;
    }
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
        width: auto;
        max-width: 100%;
    }
    [data-testid="stChatMessageAvatarCustom"] {
        width: 2rem;
        height: 2rem;
        flex-basis: 2rem;
        border-radius: 10px !important;
    }
    [data-testid="stChatMessageContent"] {
        font-size: 0.92rem;
        line-height: 1.6;
    }
    [data-testid="stChatInput"] > div {
        padding: 5px 8px !important;
    }
    [data-testid="stChatInput"] textarea {
        font-size: 0.92rem !important;
    }
    [data-testid="stBottom"] {
        padding-left: 0.5rem;
        padding-right: 0.5rem;
    }
}
</style>
""", unsafe_allow_html=True)

# --- 4. SESSION STATE ---
st.session_state.setdefault("messages", [])
st.session_state.setdefault("quick_prompt", None)
st.session_state.setdefault("active_source_name", None)
st.session_state.setdefault("chunk_count", None)
st.session_state.setdefault("current_chat_id", None)
st.session_state.setdefault("pending_delete", None)  # kis chat ka delete confirm hona baqi hai
st.session_state.setdefault("upload_notice_signature", None)
st.session_state.setdefault("indexed_file_names", [])


def reset_active_view():
    st.session_state["messages"] = []
    st.session_state["current_chat_id"] = None
    st.session_state["active_source_name"] = None
    st.session_state["chunk_count"] = None


# --- 5. SIDEBAR ---
st.sidebar.markdown(
    f'<div class="brand"><div class="brand-mark" aria-hidden="true">'
    '<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">'
    '<path d="M8 4.75h10l6 6v8.5" stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>'
    '<path d="M18 4.75v6h6M8 4.75v22.5h8" stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>'
    '<path d="M11.5 15h7M11.5 19h4.5" stroke="white" stroke-width="1.6" stroke-linecap="round"/>'
    '<circle cx="22" cy="21" r="4.25" stroke="white" stroke-width="1.8"/>'
    '<path d="m25.1 24.1 3.15 3.15" stroke="white" stroke-width="2" stroke-linecap="round"/>'
    '</svg></div>'
    f'<div><div class="brand-name">{APP_NAME}</div>'
    f'<div class="brand-sub">Code & Document Assistant</div></div></div>',
    unsafe_allow_html=True
)

if st.sidebar.button(":material/add: New Chat Session", use_container_width=True):
    reset_active_view()
    st.session_state["pending_delete"] = None
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown(
    '<div class="side-title">Upload Source</div>'
    '<div class="side-help">Upload code files or PDFs to get started.</div>',
    unsafe_allow_html=True
)

uploaded_files = st.sidebar.file_uploader(
    "Upload code files or PDFs",
    accept_multiple_files=True,
    type=["py", "js", "ts", "tsx", "jsx", "json", "md", "html", "css", "pdf"],
    label_visibility="collapsed"
)

target_load_path = None
is_input_valid = False

if uploaded_files:
    upload_signature = tuple(
        (uploaded_file.name, hashlib.sha256(uploaded_file.getvalue()).hexdigest())
        for uploaded_file in uploaded_files
    )
    if upload_signature != st.session_state["upload_notice_signature"]:
        st.toast(
            f"{len(uploaded_files)} file(s) loaded successfully!",
            icon=":material/check_circle:",
            duration=5,
        )
        st.session_state["upload_notice_signature"] = upload_signature

    upload_dir = "data/user_uploads"
    os.makedirs(upload_dir, exist_ok=True)
    for f in os.listdir(upload_dir):
        file_path = os.path.join(upload_dir, f)
        if os.path.isfile(file_path):
            os.remove(file_path)

    for uploaded_file in uploaded_files:
        with open(os.path.join(upload_dir, uploaded_file.name), "wb") as f:
            f.write(uploaded_file.getbuffer())
    target_load_path = upload_dir
    is_input_valid = True
else:
    st.session_state["upload_notice_signature"] = None

# Jab tak file upload nahi hoti, index button nahi dikhega.
index_button = False
if is_input_valid:
    index_button = st.sidebar.button(
        ":material/library_add: Index Files",
        type="primary",
        use_container_width=True,
    )

if index_button:
    with st.sidebar:
        with st.spinner("Processing files and building vector index..."):
            try:
                logger.info(f"Starting indexing for source: {target_load_path}")
                docs = load_codebase(target_load_path)

                if not docs:
                    st.error("No valid code or PDF files found.")
                else:
                    chunks = split_code_documents(docs)
                    create_vector_store(chunks)

                    if len(uploaded_files) == 1:
                        source_name = uploaded_files[0].name
                    else:
                        source_name = f"{uploaded_files[0].name} (+{len(uploaded_files)-1} more)"

                    st.session_state["active_source_name"] = source_name
                    st.session_state["chunk_count"] = len(chunks)
                    st.session_state["indexed_file_names"] = [
                        uploaded_file.name for uploaded_file in uploaded_files
                    ]

                    chat_title = source_name if len(source_name) < 30 else source_name[:27] + "..."
                    chat_id = create_chat(chat_title)
                    st.session_state["current_chat_id"] = chat_id
                    st.session_state["messages"] = []

                    st.toast(
                        f"Successfully indexed {len(chunks)} chunks.",
                        icon=":material/task_alt:",
                        duration=5,
                    )
            except Exception as e:
                st.error(f"Indexing failed: {e}")
                logger.error(f"Error: {e}", exc_info=True)

if st.session_state["indexed_file_names"]:
    st.sidebar.markdown(
        '<div class="indexed-files"><div class="indexed-files-title">Indexed files</div>'
        + "".join(
            '<div class="indexed-file"><span class="indexed-file-icon">'
            '<svg viewBox="0 0 20 20" fill="none" aria-hidden="true" xmlns="http://www.w3.org/2000/svg">'
            '<path d="M5 2.5h6l4 4v11H5v-15Z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>'
            '<path d="M11 2.75V7h4M7.5 10h5M7.5 13h5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>'
            '</svg></span><span>'
            f'{html.escape(file_name)}</span></div>'
            for file_name in st.session_state["indexed_file_names"]
        )
        + '</div>',
        unsafe_allow_html=True,
    )

# --- Chat History Section in Sidebar ---
st.sidebar.markdown("---")
st.sidebar.markdown("### :material/forum: Chat History")

past_chats = []
try:
    past_chats = get_chats()
except Exception as e:
    logger.error(f"History load failed: {e}", exc_info=True)
    st.sidebar.warning("Could not load chat history.")

if past_chats:
    for chat in past_chats:
        cid = chat["id"]
        title = chat["title"]

        # --- Delete confirmation mode ---
        if st.session_state["pending_delete"] == cid:
            st.sidebar.markdown(
                f'<div class="confirm-box"><div class="confirm-title">Delete this chat?</div>'
                f'<div class="confirm-detail">{html.escape(title)} will be permanently deleted.</div></div>',
                unsafe_allow_html=True
            )
            c_yes, c_no = st.sidebar.columns(2)
            if c_yes.button(
                ":material/delete: Delete",
                key=f"yes_{cid}",
                type="primary",
                use_container_width=True,
            ):
                try:
                    delete_chat(cid)
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

        # --- Normal row: [chat title][trash] ---
        is_active = st.session_state["current_chat_id"] == cid
        label = ("▶ " if is_active else "") + title
        col_chat, col_del = st.sidebar.columns([5, 1])
        if col_chat.button(label, key=f"open_{cid}", use_container_width=True):
            st.session_state["current_chat_id"] = cid
            db_messages = get_messages(cid)
            st.session_state["messages"] = [{"role": m["role"], "content": m["content"]} for m in db_messages]
            st.session_state["active_source_name"] = title
            st.rerun()
        if col_del.button(
            ":material/delete_outline:",
            key=f"del_{cid}",
            help="Yeh chat delete karein",
            use_container_width=True,
        ):
            st.session_state["pending_delete"] = cid
            st.rerun()
elif not past_chats:
    st.sidebar.info("No past chats found.")

st.sidebar.markdown(
    '<div class="side-note">Answers are grounded in the files you indexed.</div>',
    unsafe_allow_html=True
)

# --- 6. ACTIVE CONTEXT BANNER ---
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

# --- 7. HERO ---
st.markdown(
    f'<div class="hero"><h1>{APP_TAGLINE}</h1>'
    f'<p>Upload code, PDFs, or documents. {APP_NAME} finds the relevant context '
    f'and answers using your files, with clear source references.</p></div>',
    unsafe_allow_html=True
)

# --- 8. CHAT INTERFACE ---
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

if prompt:
    if not st.session_state.get("current_chat_id"):
        chat_id = create_chat("General Chat")
        st.session_state["current_chat_id"] = chat_id

    st.session_state.messages.append({"role": "user", "content": prompt})
    save_message(st.session_state["current_chat_id"], "user", prompt)

    render_chat_message({"role": "user", "content": prompt})

    with st.chat_message("assistant", avatar=":material/smart_toy:"):
        with st.spinner("Analyzing documents..."):
            try:
                chain, _ = get_rag_chain()
                response = chain.invoke(prompt)
                st.markdown(response)

                st.session_state.messages.append({"role": "assistant", "content": response})
                save_message(st.session_state["current_chat_id"], "assistant", response)
            except Exception as e:
                err_msg = f"**Error:** Index files first or check API key.\n```text\n{e}\n```"
                st.markdown(err_msg)
                st.session_state.messages.append({"role": "assistant", "content": err_msg})