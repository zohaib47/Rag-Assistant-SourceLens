# 🔭 DocuLens

> *Peek inside your files and ask them anything.*

DocuLens is a **local Document & Code RAG assistant**. Upload your own code files
(`.py`, `.js`, `.ts`, `.tsx`, `.jsx`, `.json`, `.md`, `.html`, `.css`) or PDFs, and the AI answers
your questions using only what is inside those files.

## ✨ Features

- 📁 **Local code & PDF Q&A**: ask about functions, logic, and documentation in your own files
- 🛡️ **Strict guardrails**: answers come only from the uploaded files, with no made-up information
- 🧩 **Code-aware chunking**: Python/JS/TS code is split along function and class boundaries
- 📄 **File and page references**: every answer names the source file (and the page number for PDFs)
- 💬 **Chat history**: stored in Supabase, with rename and delete support
- 🗑️ **Safe deletion**: two-step confirmation per chat, plus a "Danger Zone" to delete all chats

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

1. **Load**: files are read from the upload folder (PDFs page by page)
2. **Chunk**: content is split into overlapping chunks, using language-aware splitters for code
3. **Embed & store**: chunks are embedded locally and stored in Supabase pgvector
4. **Retrieve**: the top 4 most relevant chunks are fetched for each question
5. **Answer**: Groq's LLM answers using only the retrieved context and cites the file names

## 📂 Project Structure

```text
doculens/
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
    └── database.py
```

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

Run this in the Supabase **SQL Editor**:

```sql
create extension if not exists vector;

create table if not exists chats (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  created_at timestamptz default now()
);

create table if not exists messages (
  id uuid primary key default gen_random_uuid(),
  chat_id uuid references chats(id) on delete cascade,
  role text not null,
  content text not null,
  created_at timestamptz default now()
);

create index if not exists idx_messages_chat on messages(chat_id, created_at);
```

### 3. Configure environment variables

Create a `.env` file in the project root:

```env
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_KEY=your-supabase-key
SUPABASE_DB_URL=postgresql+psycopg://postgres:PASSWORD@db.xxxx.supabase.co:5432/postgres
GROQ_API_KEY=your-groq-api-key
GROQ_MODEL=llama-3.3-70b-versatile
```

> ⚠️ Never commit your `.env` file. It is already listed in `.gitignore`.

### 4. Run the app

```bash
streamlit run app.py
```

## 🧭 Usage

1. Upload code files or PDFs from the sidebar
2. Click **✨ OK - Index Files**
3. Ask a question in the chat box
4. Find your previous conversations under **Chat History** in the sidebar

## ⚠️ Known Limitations

- The vector store is currently shared across all chats; indexing new files replaces the previous index
- Scanned (image-only) PDFs are not supported because text extraction needs OCR
- The free Groq tier has rate limits

## 🗺️ Roadmap

- [ ] A separate vector collection for each chat
- [ ] Show source snippets alongside answers
- [ ] Export chats (Markdown / PDF)
- [ ] User authentication with Supabase Auth

## 📜 License

MIT