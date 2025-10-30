import hashlib
import re
import shutil
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional

import cohere
import html2text
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS

from embeddings.cohere_embedding import CohereEmbedding
from scripts import get_api_key, write_to_file
from settings import prompts
from settings.logger import get_logger
from settings.rag_config import *

logger = get_logger(__name__)


class BaseRAG(ABC):
    def __init__(
        self,
        content_path: Path,
        index_path: Optional[str] = None,
        rerank: bool = False,
        chunking_type: str = "recursive",
    ):
        self.rerank = rerank
        self.index_path = index_path or "indexes"
        self.embedder = CohereEmbedding()

        logger.info(f"Initializing RAG system. Model temperature {TEMPERATURE}...")

        self._initialize_models()

        if self.rerank:
            logger.info("Using Cohere's re-ranking model...")
            self.reranker = cohere.Client(get_api_key.get_key("COHERE"))

        if content_path:
            logger.info("Loading knowledge base...")
            self.vectorstore = self._load_or_create_vectorstore(
                content_path, index_path
            )
            self.current_index_path = self._get_index_path(content_path)

    @abstractmethod
    def _initialize_models(self):
        pass

    def _create_embeddings(self, texts: list, is_query: bool = False) -> list:
        return self.embedder.embed(texts, is_query)

    def _get_index_path(self, content_path: Path) -> str:
        """Generate unique index path based on content."""
        content_hash = (
            hashlib.sha256(str(content_path).encode("utf-8")).hexdigest(),
            16,
        )[0][:15]
        return str(Path(self.index_path) / f"index_{content_hash}.faiss")

    def _generate_system_prompt(
        self,
        query: str,
        user_id: str,
        context: str,
        include_query: bool = True,
        include_context: bool = True,
        include_prev_conv: bool = True,
    ) -> str:
        """Generate a standardized system prompt for all LLMs."""
        system_prompt = prompts.SYS_MSG

        if include_context and context:
            system_prompt += f"\n\n### Context: \n{context}"

        # if include_prev_conv:
        #     previous_conversation = self.db.get_chat_history(user_id)
        #     system_prompt += f"\n\n### Previous conversation:\n{previous_conversation}"

        if include_query and query:
            system_prompt += f"\n\n### Current question: {query}"

        return system_prompt.strip()

    def _rerank_docs(self, query: str, docs):
        """
        Refine the top-k retrieved chunks for relevance
        before passing to the LLM.
        """
        docs_list = [doc.page_content for doc in docs]
        reranked = self.reranker.rerank(
            model="rerank-multilingual-v3.0",
            query=query,
            documents=docs_list,
            top_n=3,
            return_documents=True,
        )
        return reranked

    def _find_relevant_context(self, query: str, top_k: int = 5) -> str:
        """Find relevant context using similarity search."""
        query_embedding = self._create_embeddings([query], is_query=True)[0]

        docs = self.vectorstore.similarity_search_by_vector(
            query_embedding, k=top_k, fetch_k=20
        )
        if self.rerank:
            reranked_docs = self._rerank_docs(query, docs)
            return "\n\n".join(
                [result.document.text for result in reranked_docs.results]
            )

        return "\n\n".join([doc.page_content for doc in docs])

    def _load_or_create_vectorstore(
        self, content_path: Path, index_path: Path = None
    ) -> FAISS:
        """Load existing index or create new one."""
        if index_path is not None:
            return self._load_vectorstore(index_path)

        index_path = self._get_index_path(content_path)

        if Path(index_path).exists():
            logger.info(f"Loading existing index from {index_path}")
            return self._load_vectorstore(index_path)

        logger.info("Creating new index...")
        return self._create_vectorstore(content_path)

    def _create_vectorstore(self, content_path: Path) -> FAISS:
        """Create FAISS vectorstore from content with incremental embedding saving."""
        with open(content_path, "r", encoding="utf-8") as f:
            content = f.read()

        cleaned_content = self._clean_html_content(content)
        chunks = self._create_chunks(cleaned_content)
        logger.info(f"Created {len(chunks)} chunks")

        temp_index_path = self._get_index_path(content_path) + ".temp"
        temp_progress_path = self._get_index_path(content_path) + ".progress"

        if Path(temp_index_path).exists() and Path(temp_progress_path).exists():
            logger.info(f"Found existing progress, resuming from previous state")
            with open(temp_progress_path, "r") as f:
                processed_chunks = int(f.read().strip())

            vectorstore = self._load_vectorstore(temp_index_path)

            remaining_chunks = chunks[processed_chunks:]
            start_idx = processed_chunks
        else:
            processed_chunks = 0
            remaining_chunks = chunks
            start_idx = 0

            if remaining_chunks:
                first_chunk = remaining_chunks[0]
                first_embedding = self._create_embeddings([first_chunk])[0]
                text_embeddings = [(first_chunk, first_embedding)]

                vectorstore = FAISS.from_embeddings(
                    text_embeddings=text_embeddings,
                    embedding=self._create_embeddings,
                    metadatas=[{"source": f"chunk_{start_idx}"}],
                )

                processed_chunks = 1
                start_idx = 1
                remaining_chunks = remaining_chunks[1:]
            else:
                logger.warning("No chunks to process, creating empty vectorstore")
                dummy_text = "Initialization placeholder"
                dummy_embedding = self._create_embeddings([dummy_text])[0]
                vectorstore = FAISS.from_embeddings(
                    text_embeddings=[(dummy_text, dummy_embedding)],
                    embedding=self._create_embeddings,
                    metadatas=[{"source": "initialization_placeholder"}],
                )

        batch_size = 10

        for i in range(0, len(remaining_chunks), batch_size):
            batch = remaining_chunks[i : i + batch_size]

            try:
                batch_embeddings = self._create_embeddings(batch)
                text_embeddings = list(zip(batch, batch_embeddings))

                vectorstore.add_embeddings(
                    text_embeddings=text_embeddings,
                    metadatas=[
                        {"source": f"chunk_{start_idx + j}"} for j in range(len(batch))
                    ],
                )

                processed_chunks = start_idx + i + len(batch)

                # with open(temp_progress_path, "w") as f:
                #     f.write(str(processed_chunks))

                write_to_file.write(
                    str(processed_chunks),
                    temp_progress_path,
                )

                self._save_vectorstore(vectorstore, temp_index_path)

                logger.info(
                    f"Saved progress: {processed_chunks}/{len(chunks)} chunks processed"
                )

            except Exception as e:
                logger.error(f"Error while processing batch: {e}")
                logger.info(f"Progress saved up to chunk {processed_chunks}")
                return vectorstore

            time.sleep(3)

        final_index_path = self._get_index_path(content_path)
        self._save_vectorstore(vectorstore, final_index_path)

        try:
            # Path(temp_index_path).rmdir()
            shutil.rmtree(temp_index_path, ignore_errors=True)
            Path(temp_progress_path).unlink(missing_ok=True)
        except Exception as e:
            logger.warning(f"Failed to clean up temporary files: {e}")

        logger.info(
            f"Vectorstore creation completed successfully with {len(chunks)} chunks"
        )
        return vectorstore

    def _clean_html_content(self, content: str) -> str:
        """Clean HTML content and convert to markdown."""
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = False
        h.ignore_tables = False

        content = h.handle(content)
        content = re.sub(r"(\w)-\n(\w)", r"\1\2", content)
        content = re.sub(r"(?<!\n)\n(?!\n)", " ", content)
        content = re.sub(r"\n{3,}", "\n\n", content)
        content = re.sub(r"\[(\w+)\]\(([^)]+)\)", r"\1 (\2)", content)

        return content.strip()

    def _load_vectorstore(self, path: Path) -> FAISS:
        """Load vectorstore from disk."""
        return FAISS.load_local(
            path, self._create_embeddings, allow_dangerous_deserialization=True
        )

    def _save_vectorstore(self, vectorstore: FAISS, path: Path) -> None:
        """Save vectorstore to disk."""
        logger.info(f"Saving index to {path}")
        vectorstore.save_local(path)

    def _create_chunks(self, text: str) -> List[str]:
        """Create chunks using the specified chunking method."""
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", " ", ""],
        )

        logger.info("Splitting data using langchain's RecursiveCharacterTextSplitter")
        return splitter.split_text(text)
