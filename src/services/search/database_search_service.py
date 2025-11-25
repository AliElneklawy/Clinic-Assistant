from rag.rag_system import RAGSystem


class DatabaseSearchService:
    def __init__(self, rag: RAGSystem):
        self.rag = rag

    def search(self, query: str) -> dict:
        """Internal method to search database and return structured data."""
        result = self.rag.find_relevant_context_with_sources(query=query)

        sources = result.get("sources", [])
        max_relevance_score = 0.0
        has_relevance_scores = False

        for source in sources:
            if "relevance_score" in source:
                has_relevance_scores = True
                max_relevance_score = max(
                    max_relevance_score, source["relevance_score"]
                )

        return {
            "response": result.get("response", ""),
            "sources": sources,
            "max_relevance_score": max_relevance_score,
            "has_relevance_scores": has_relevance_scores,
        }
