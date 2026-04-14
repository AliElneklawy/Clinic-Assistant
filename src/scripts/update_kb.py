import sys
from pathlib import Path

# Add the src directory to the Python path
src_dir = Path(__file__).parent.parent
sys.path.insert(0, str(src_dir))

from src.rag.rag_system import RAGSystem
from src.settings.paths import DISEASE_CONDITION_FILE, DRUGS_SUPPS_FILE, INDEXES_DIR


def read_file(file_path):
    with open(file_path, "r") as f:
        return f.read()


def update_vectorstore(rag: RAGSystem, content: str):
    rag.update_vectorstore(content)


if __name__ == "__main__":
    rag = RAGSystem(
        content_path=DRUGS_SUPPS_FILE,
        index_path=INDEXES_DIR,  # / "index_7ad274e90429ac4.faiss.temp"
    )
    new_content = read_file(DRUGS_SUPPS_FILE)
    update_vectorstore(rag, new_content)
