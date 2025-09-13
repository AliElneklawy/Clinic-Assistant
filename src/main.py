import asyncio

from crawler import AsyncCrawler
from rag.cohere_rag import CohereRAG
from settings.logger import get_logger
from settings.paths import DATA_DIR, INDEXES_DIR, MED_DATA_FILE
from utils.file_loader import FileLoader

logger = get_logger(__name__)


async def fetch_from_web():
    link = "https://www.news-medical.net/"

    crawler = AsyncCrawler(link, max_concurrent_requests=15)
    try:
        content_path = await crawler.extract_content(link, max_depth=3)  # noqa: F841
    finally:
        await crawler.close()


def load_from_files():
    content_dir = DATA_DIR / "content"

    loader = FileLoader(content_dir, MED_DATA_FILE, "docling")
    docs = loader.extract_from_file()

    if not docs:
        logger.warning("No docs were retrieved.")


def test_web_search():
    pass


async def test_rag(rag, user_id="1234"):
    while True:
        query = input("User: ").strip()
        if not query:
            continue
        if query.lower() == "quit":
            break

        try:
            response = await rag.get_response(query, user_id)
            print("Assistant:", response)
        except Exception as e:
            print(f"Error: {e}")


def main():
    # load_from_files()
    # asyncio.run(fetch_from_web())

    rag = CohereRAG(MED_DATA_FILE, INDEXES_DIR, chunking_type="recursive", rerank=False)
    asyncio.run(test_rag(rag))


if __name__ == "__main__":
    main()
