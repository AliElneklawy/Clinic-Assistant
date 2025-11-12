MAX_SEARCH_RESULTS = (
    3  # Maximum number of search results to retrieve from Tavily search
)
RELEVANCE_THRESHOLD = 0.6  # Minimum relevance score of retrieved info from the knowledge base (calculated using cohere's reranker)
LAST_N_MESSAGES = 6  # Number of last messages to be sent to the agent
