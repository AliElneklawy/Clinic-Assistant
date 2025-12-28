def format_response_with_sources(
    response_text: str, sources: list, max_relevance: float, has_scores: bool
) -> str:
    """Format response with concise source citations."""
    formatted = f"{response_text}"

    if sources:
        formatted += "\n\nSources:"
        for idx, source in enumerate(sources, 1):
            text_preview = source.get("text", "")[:150]
            if len(source.get("text", "")) > 150:
                text_preview += "..."
            formatted += f"\n[{idx}] {text_preview}"
            if "relevance_score" in source:
                formatted += f" (score: {source['relevance_score']:.2f})"

    return formatted
