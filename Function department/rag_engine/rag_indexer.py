# Function department/rag_engine/rag_indexer.py
import os
import sys
import re
import json
import sqlite3
import math
from typing import List, Dict, Any
from dotenv import load_dotenv

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

class DocumentChunker:
    """Chunks documents into semantic blocks (paragraphs or header-based chunks)."""

    def __init__(self, chunk_size: int = 500, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk_text(self, text: str, source_doc: str) -> List[Dict[str, Any]]:
        chunks = []
        # Split by headers if markdown, else double linebreaks
        paragraphs = re.split(r'\n\s*\n', text)
        
        current_chunk = ""
        chunk_idx = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            if len(current_chunk) + len(para) <= self.chunk_size:
                current_chunk += ("\n\n" if current_chunk else "") + para
            else:
                if current_chunk:
                    chunks.append({
                        "chunk_id": f"{source_doc}_chunk_{chunk_idx}",
                        "source": source_doc,
                        "text": current_chunk,
                        "token_count": len(current_chunk.split())
                    })
                    chunk_idx += 1
                current_chunk = para

        if current_chunk:
            chunks.append({
                "chunk_id": f"{source_doc}_chunk_{chunk_idx}",
                "source": source_doc,
                "text": current_chunk,
                "token_count": len(current_chunk.split())
            })

        return chunks

class RAGIndexer:
    """Indexes document chunks into an SQLite vector store using TF-IDF and word embeddings."""

    def __init__(self, db_path: str = None, docs_dir: str = None):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.docs_dir = docs_dir or os.path.join(base_dir, "data", "documents")
        self.db_path = db_path or os.path.join(base_dir, "data", "database", "rag_index.db")
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        os.makedirs(self.docs_dir, exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id TEXT PRIMARY KEY,
                source TEXT,
                text TEXT,
                terms_json TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def tokenize(self, text: str) -> List[str]:
        words = re.findall(r'\w+', text.lower())
        return [w for w in words if len(w) > 1]

    def index_documents(self):
        chunker = DocumentChunker()
        all_chunks = []

        if not os.path.exists(self.docs_dir):
            return 0

        for root, _, files in os.walk(self.docs_dir):
            for file in files:
                if file.endswith(('.md', '.txt', '.json')):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, self.docs_dir)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            text = f.read()
                        doc_chunks = chunker.chunk_text(text, rel_path)
                        all_chunks.extend(doc_chunks)
                    except Exception as e:
                        print(f"Error reading {file}: {e}")

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("DELETE FROM chunks")

        for c in all_chunks:
            tokens = self.tokenize(c['text'])
            cur.execute(
                "INSERT INTO chunks (chunk_id, source, text, terms_json) VALUES (?, ?, ?, ?)",
                (c['chunk_id'], c['source'], c['text'], json.dumps(tokens))
            )

        conn.commit()
        conn.close()
        print(f"Successfully indexed {len(all_chunks)} chunks from {self.docs_dir}")
        return len(all_chunks)

if __name__ == "__main__":
    indexer = RAGIndexer()
    indexer.index_documents()
