from agents.query_handler_agent import QueryHandlerAgent
from settings.paths import INDEXES_DIR, MED_DATA_FILE


def run_agent(agent):
    while True:
        query = input("User: ").strip()
        if not query:
            continue
        if query.lower() == "quit":
            break

        try:
            response = agent.run(query)
            print("Assistant:", response["output"])
        except Exception as e:
            print(f"Error: {e}")


def main():
    agent = QueryHandlerAgent(
        content_path=MED_DATA_FILE,
        index_path=INDEXES_DIR / "index_7ad274e90429ac4.faiss.temp",
    )

    run_agent(agent)


if __name__ == "__main__":
    main()
