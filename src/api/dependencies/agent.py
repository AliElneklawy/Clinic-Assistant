from src.agents.query_handler_agent import QueryHandlerAgent

_agent_instance = None


def get_agent():
    global _agent_instance  # use the variable from the module’s global scope — not create a new local one

    if _agent_instance is None:
        _agent_instance = QueryHandlerAgent()

    return _agent_instance
