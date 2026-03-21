"""
RAG Vector Store — загружает .md файлы, нарезает на чанки,
создаёт эмбеддинги и ищет релевантный контекст для запроса.
"""

import os
import glob
import chromadb
from chromadb.utils import embedding_functions

KNOWLEDGE_DIR = os.path.join(os.path.dirname(__file__), "documents")
COLLECTION_NAME = "stock_analysis"


class VectorStore:
    def __init__(self):
        self.client = chromadb.Client()  # in-memory, быстро
        self.ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"  # лёгкая модель, работает локально
        )
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=self.ef,
            metadata={"hnsw:space": "cosine"},
        )
        self._loaded = False

    def load_knowledge(self):
        """Загружает все .md файлы из knowledge/ в векторную базу."""
        if self._loaded and self.collection.count() > 0:
            return

        md_files = sorted(glob.glob(os.path.join(KNOWLEDGE_DIR, "*.md")))
        if not md_files:
            print(f"[WARN] Нет .md файлов в {KNOWLEDGE_DIR}")
            return

        all_docs = []
        all_ids = []
        all_meta = []

        for filepath in md_files:
            filename = os.path.basename(filepath)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            # Нарезаем по секциям (## заголовки)
            chunks = self._split_by_sections(content, filename)

            for i, chunk in enumerate(chunks):
                doc_id = f"{filename}_{i}"
                all_docs.append(chunk["text"])
                all_ids.append(doc_id)
                all_meta.append({
                    "source": filename,
                    "section": chunk.get("section", ""),
                    "category": self._detect_category(filename),
                })

        if all_docs:
            self.collection.add(
                documents=all_docs,
                ids=all_ids,
                metadatas=all_meta,
            )
            self._loaded = True
            print(f"[OK] Загружено {len(all_docs)} чанков из {len(md_files)} файлов")

    def search(self, query: str, n_results: int = 5, category: str = None) -> list[dict]:
        """
        Ищет релевантные куски знаний по запросу.
        category: фильтр по типу анализа (technical, dcf, risk, screener и т.д.)
        """
        if self.collection.count() == 0:
            self.load_knowledge()

        where_filter = None
        if category:
            where_filter = {"category": category}

        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where_filter,
        )

        docs = []
        for i in range(len(results["documents"][0])):
            docs.append({
                "text": results["documents"][0][i],
                "source": results["metadatas"][0][i]["source"],
                "section": results["metadatas"][0][i].get("section", ""),
                "distance": results["distances"][0][i] if results.get("distances") else None,
            })
        return docs

    def search_multi(self, query: str, categories: list[str] = None, n_per_cat: int = 2) -> list[dict]:
        """
        Поиск по нескольким категориям — собирает контекст из разных методологий.
        Например: теханализ + риски + DCF = полный отчёт.
        """
        if not categories:
            return self.search(query, n_results=8)

        all_results = []
        for cat in categories:
            results = self.search(query, n_results=n_per_cat, category=cat)
            all_results.extend(results)
        return all_results

    def _split_by_sections(self, text: str, filename: str) -> list[dict]:
        """Разбивает markdown на чанки по ## заголовкам."""
        chunks = []
        current_section = ""
        current_text = []

        for line in text.split("\n"):
            if line.startswith("## "):
                # Сохраняем предыдущий чанк
                if current_text:
                    combined = "\n".join(current_text).strip()
                    if len(combined) > 50:  # пропускаем слишком короткие
                        chunks.append({"section": current_section, "text": combined})
                current_section = line.replace("## ", "").strip()
                current_text = [line]
            elif line.startswith("# ") and not line.startswith("##"):
                # Главный заголовок — начало нового документа
                if current_text:
                    combined = "\n".join(current_text).strip()
                    if len(combined) > 50:
                        chunks.append({"section": current_section, "text": combined})
                current_section = line.replace("# ", "").strip()
                current_text = [line]
            else:
                current_text.append(line)

        # Последний чанк
        if current_text:
            combined = "\n".join(current_text).strip()
            if len(combined) > 50:
                chunks.append({"section": current_section, "text": combined})

        # Если чанков мало — добавляем весь документ целиком
        if len(chunks) == 0:
            chunks.append({"section": "full", "text": text.strip()})

        return chunks

    def _detect_category(self, filename: str) -> str:
        """Определяет категорию по имени файла."""
        mapping = {
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
        }
        for key, cat in mapping.items():
            if key in filename:
                return cat
        return "general"


# Синглтон — один экземпляр на всё приложение
store = VectorStore()