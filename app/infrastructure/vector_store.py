from __future__ import annotations

import glob
import os

import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

from app.config import settings

COLLECTION_NAME = "stock_analysis"

CATEGORY_MAP = {
    "01_screener": "screener",
    "02_dcf": "dcf",
    "03_risk": "risk",
    "04_earnings": "earnings",
    "05_portfolio": "portfolio",
    "06_technical": "technical",
    "07_dividends": "dividends",
    "08_competitors": "competitors",
    "09_full_report": "master",
    "10_portfolio_user": "user_portfolio",
    "11_portfolio_blackrock": "blackrock_portfolio",
}


class VectorStore:
    def __init__(self) -> None:
        self.client = chromadb.Client()
        self.ef = DefaultEmbeddingFunction()
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=self.ef,
            metadata={"hnsw:space": "cosine"},
        )
        self._loaded = False

    def load_knowledge(self) -> None:
        if self._loaded and self.collection.count() > 0:
            return

        md_files = sorted(glob.glob(os.path.join(settings.documents_dir, "*.md")))
        if not md_files:
            print(f"[WARN] Нет .md файлов в {settings.documents_dir}")
            return

        all_docs, all_ids, all_meta = [], [], []
        for filepath in md_files:
            filename = os.path.basename(filepath)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            for i, chunk in enumerate(self._split_by_sections(content)):
                all_docs.append(chunk["text"])
                all_ids.append(f"{filename}_{i}")
                all_meta.append({
                    "source": filename,
                    "section": chunk.get("section", ""),
                    "category": self._detect_category(filename),
                })

        if all_docs:
            self.collection.add(documents=all_docs, ids=all_ids, metadatas=all_meta)
            self._loaded = True
            print(f"[OK] Загружено {len(all_docs)} чанков из {len(md_files)} файлов")

    def search(self, query: str, n_results: int = 5, category: str | None = None) -> list[dict]:
        if self.collection.count() == 0:
            self.load_knowledge()

        where_filter = {"category": category} if category else None
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where_filter,
        )
        return [
            {
                "text": results["documents"][0][i],
                "source": results["metadatas"][0][i]["source"],
                "section": results["metadatas"][0][i].get("section", ""),
                "distance": results["distances"][0][i] if results.get("distances") else None,
            }
            for i in range(len(results["documents"][0]))
        ]

    def search_multi(self, query: str, categories: list[str] | None = None, n_per_cat: int = 2) -> list[dict]:
        if not categories:
            return self.search(query, n_results=8)
        results = []
        for cat in categories:
            results.extend(self.search(query, n_results=n_per_cat, category=cat))
        return results

    def _split_by_sections(self, text: str) -> list[dict]:
        chunks: list[dict] = []
        current_section = ""
        current_text: list[str] = []

        def _flush() -> None:
            combined = "\n".join(current_text).strip()
            if len(combined) > 50:
                chunks.append({"section": current_section, "text": combined})

        for line in text.split("\n"):
            if line.startswith("## "):
                _flush()
                current_section = line[3:].strip()
                current_text = [line]
            elif line.startswith("# ") and not line.startswith("##"):
                _flush()
                current_section = line[2:].strip()
                current_text = [line]
            else:
                current_text.append(line)

        _flush()
        if not chunks:
            chunks.append({"section": "full", "text": text.strip()})
        return chunks

    def _detect_category(self, filename: str) -> str:
        for key, cat in CATEGORY_MAP.items():
            if key in filename:
                return cat
        return "general"


rag_store = VectorStore()
