import asyncio

from agents.query_handler_agent import QueryHandlerAgent
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
    # rag = CohereRAG(MED_DATA_FILE, INDEXES_DIR, chunking_type="recursive", rerank=False)
    # asyncio.run(test_rag(rag))
    agent = QueryHandlerAgent(content_path=MED_DATA_FILE,
                              index_path=INDEXES_DIR / "index_7ad274e90429ac4.faiss.temp")
    result = agent.run("I have a really bad headache. What should I do?")

    print(result)

if __name__ == "__main__":
    main()
