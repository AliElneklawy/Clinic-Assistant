import asyncio

from settings.paths import INDEXES_DIR, MED_DATA_FILE
from rag.cohere_rag import CohereRAG
from utils.file_loader import FileLoader

def fetch_from_web():
    pass

def load_from_files():
    pass

def test_web_search():
    pass

async def test_rag(rag, user_id='1234'):
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
    rag = CohereRAG(MED_DATA_FILE, INDEXES_DIR, chunking_type="recursive", rerank=False)
    asyncio.run(test_rag(rag))

if __name__ == "__main__":
    main()
