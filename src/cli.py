from uuid import uuid4

from src.agents.query_handler_agent import QueryHandlerAgent


def run_agent(agent, user_id):
    while True:
        query = input("User: ").strip()
        if not query:
            continue
        if query.lower() == "quit":
            break

        try:
            response = agent.run(query, user_id)
            print("Assistant:", response["output"])
        except Exception as e:
            print(f"Error: {e}")


def main():
    agent = QueryHandlerAgent()
    run_agent(agent, str(uuid4()))


if __name__ == "__main__":
    main()
