# 🔭 SourceLens

> *Peek inside your files and ask them anything.*

SourceLens is a **Document, Code & Spreadsheet RAG assistant**. Upload code files
(`.py`, `.js`, `.ts`, `.tsx`, `.jsx`, `.json`, `.md`, `.html`, `.css`), PDFs, or
Excel workbooks (`.xlsx`, `.xlsm`, `.xls`), then ask questions grounded in their content.

## ✨ Features

- 📁 **Code, PDF & Excel Q&A**: ask about code, documents, spreadsheet rows, and workbook sheets
- 📚 **Per-file indexing**: files have separate indexes; select an indexed file to open its chat
- 🛡️ **Grounded answers**: responses use retrieved content from your indexed files
- 🧩 **Code-aware chunking**: Python/JS/TS code is split along function and class boundaries
- 📄 **File and page references**: every answer names the source file (and the page number for PDFs)
- 💬 **Saved chat history**: create an account or log in to keep and revisit conversations
- 🔐 **Account access**: users can create an account or log in using the custom `users` table
- ♻️ **Duplicate indexing protection**: unchanged files are not indexed again
- 🗑️ **Safe deletion**: two-step confirmation before deleting a chat

## 🧱 Tech Stack

| Layer | Technology |
|---|---|
| UI | Streamlit |
| LLM | Groq (`llama-3.3-70b-versatile`) |
| Embeddings | HuggingFace `all-MiniLM-L6-v2` (runs locally) |
| Vector DB | Supabase pgvector via `langchain-postgres` |
| Chat storage | Supabase (`chats` and `messages` tables) |
| Orchestration | LangChain (LCEL) |

## ⚙️ How It Works

1. **Load**: uploaded files are saved under `data/user_uploads`; PDFs are read page by page and Excel workbooks sheet by sheet
2. **Chunk**: content is split into overlapping chunks, using language-aware splitters for code
3. **Embed & store**: chunks are embedded locally and stored in Supabase pgvector
4. **Retrieve**: the top 4 most relevant chunks are fetched for each question
5. **Answer**: Groq's LLM answers using only the retrieved context and cites the file names

## 📂 Project Structure

```text
SourceLens/
├── app.py
├── requirements.txt
├── .env
├── .gitignore
├── README.md
├── data/
│   └── user_uploads/
└── src/
    ├── __init__.py
    ├── loader.py
    ├── chunker.py
    ├── vectorstore.py
    ├── rag_pipeline.py
    ├── database.py
    └── chat_delete.py
```

Uploaded files are stored locally in `data/user_uploads/`. Embeddings are stored
in Supabase pgvector; `vector_db/` is not the active vector store.

## 🚀 Getting Started

### 1. Clone and install

```bash
git clone https://github.com/zohaib47/Rag-Assistant-SourceLens.git
cd Rag-Assistant-SourceLens
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux
pip install -r requirements.txt
```

### 2. Set up Supabase

Create a Supabase project with the `vector` extension and the tables below. If you
already ran this schema and the tables exist, keep them; do not drop or recreate them.

```sql
create extension if not exists vector;

create table if not exists users (
  id uuid primary key default gen_random_uuid(),
  email text unique not null,
  password text not null,
  created_at timestamp with time zone default timezone('utc'::text, now())
);

create table if not exists chats (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  title text not null,
  created_at timestamp with time zone default timezone('utc'::text, now())
);

create table if not exists messages (
  id uuid primary key default gen_random_uuid(),
  chat_id uuid references chats(id) on delete cascade,
  role text not null,
  content text not null,
  created_at timestamp with time zone default timezone('utc'::text, now())
);

alter table users disable row level security;
alter table chats disable row level security;
alter table messages disable row level security;

create index if not exists idx_messages_chat on messages(chat_id, created_at);
create index if not exists idx_chats_user on chats(user_id, created_at desc);
```

Accounts are stored in the custom `users` table, not Supabase Auth. The app provides
both **Create account** and **Log in** options. Signup requires a valid email and a
password of at least 6 characters; confirmation must match. Passwords are stored as
salted PBKDF2-SHA256 hashes. If an account has a legacy plaintext password, it is
upgraded to a hash after successful login.

The app accesses these tables from the Python server using `SUPABASE_KEY`. The
schema above disables row-level security (RLS), so never expose this key in browser
code or commit it. For a public deployment, enable and configure RLS or use a
trusted backend with appropriately restricted database access.

### 3. Configure environment variables

Create a `.env` file in the project root:

```env
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_KEY=your-supabase-key
SUPABASE_DB_URL=postgresql+psycopg://postgres:<database-password>@db.<project-ref>.supabase.co:5432/postgres
GROQ_API_KEY=your-groq-api-key
GROQ_MODEL=llama-3.3-70b-versatile
```

Replace the placeholders with your project credentials. If the database password
contains special characters, URL-encode them in `SUPABASE_DB_URL`.

> **Keep credentials private.** Never commit `.env` or expose Supabase/Groq keys in
> client-side code. `.env` is listed in `.gitignore`.

### 4. Run the app

```bash
streamlit run app.py
```

## 🧭 Usage

1. Click **Log in** in the app header. Choose **Create account** for a first-time
   account, or **Log in** if you already have one.
2. Upload one or more code files, PDFs, or Excel workbooks (`.xlsx`, `.xlsm`,
   `.xls`) from the sidebar and click **Index Files**. The upload control clears
   after indexing, and each file appears under **Indexed files**.
3. Select a file under **Indexed files** to open its conversation. Questions are
   answered from that file's index only; workbook sheets and rows are searchable.
4. Select another indexed file to switch its chat and context. Find all conversations
   under **History**. Guest chats remain in the current browser session; account
   chats are stored in Supabase.

## ⚠️ Known Limitations

- Each indexed file has its own vector collection and conversation. Re-indexing an
  unchanged file is skipped.
- Files indexed by older versions used a shared collection; re-upload those files
  once after upgrading to create separate indexes.
- Scanned (image-only) PDFs are not supported because text extraction needs OCR
- The free Groq tier has rate limits

## 🗺️ Roadmap

- [ ] A separate vector collection for each chat
- [ ] Show source snippets alongside answers
- [ ] Export chats (Markdown / PDF)
- [x] Account signup and login with custom-table accounts

## 📜 License

MIT