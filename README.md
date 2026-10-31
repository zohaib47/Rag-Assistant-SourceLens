# 🔭 DocuLens

> *Apni files ke andar jhaank kar sawaal poochein.*

DocuLens ek **local Document & Code RAG Assistant** hai. Aap apne system se code files
(`.py`, `.js`, `.ts`, `.tsx`, `.jsx`, `.json`, `.md`, `.html`, `.css`) ya PDFs upload karte hain,
aur AI unhi files ke andar se precise jawab deta hai.

## ✨ Features

- 📁 **Local Code & PDF Q&A**: functions, logic aur documentation par sawal poochein
- 🛡️ **Strict Guardrails**: jawab sirf upload ki hui files se aata hai, farzi jawab nahi
- 🧩 **Code-aware chunking**: Python/JS/TS code functions aur classes ki hudood par toota jata hai
- 📄 **File aur page references**: har jawab mein file ka naam (PDF mein page number bhi)
- 💬 **Chat history**: Supabase mein save, rename aur delete options ke sath
- 🗑️ **Safe delete**: har chat par 2-step confirm, aur "Danger Zone" mein saari chats delete

## 🧱 Tech Stack

| Layer | Technology |
|---|---|
| UI | Streamlit |
| LLM | Groq (`llama-3.3-70b-versatile`) |
| Embeddings | HuggingFace `all-MiniLM-L6-v2` (local) |
| Vector DB | Supabase pgvector via `langchain-postgres` |
| Chat storage | Supabase (`chats`, `messages` tables) |
| Orchestration | LangChain (LCEL) |

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

## 🚀 Setup

1. **Clone aur environment**
   ```bash
   git clone <your-repo-url>
   cd doculens
   python -m venv venv
   venv\Scripts\activate        # Windows
   pip install -r requirements.txt
   ```

2. **Supabase**: SQL Editor mein yeh chalayein:
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

3. **`.env`** file banayein:
   ```env
   SUPABASE_URL=...
   SUPABASE_KEY=...
   SUPABASE_DB_URL=postgresql+psycopg://postgres:PASSWORD@db.xxxx.supabase.co:5432/postgres
   GROQ_API_KEY=...
   GROQ_MODEL=llama-3.3-70b-versatile
   ```

4. **Run**
   ```bash
   streamlit run app.py
   ```

## 🧭 Kaise use karein

1. Sidebar mein files ya PDFs upload karein
2. **✨ OK - Index Files** dabayein
3. Neeche chat box mein sawal poochein
4. Purani chats sidebar ke **Chat History** mein milti hain

## ⚠️ Known Limitations

- Vector store abhi sab chats ke liye **ek hi** hai; naya index purane ko replace karta hai
- Scanned (image-only) PDFs ka text extract nahi hota; OCR chahiye
- Free Groq tier par rate limits ho sakti hain

## 🗺️ Roadmap

- [ ] Har chat ki apni alag vector collection
- [ ] Jawab ke sath source snippets dikhana
- [ ] Chat export (Markdown / PDF)

## 📜 License

MIT