from typing import Dict, List

CHUNK_SIZE: int = 1500
TEMPERATURE: float = 0.0
CHUNK_OVERLAP: int = 150
MAX_OUT_TOKENS: int = 1500
EMBED_BATCH_SIZE: int = 10


# class LLMConfig:
#     AVAILABLE_MODELS: Dict[str, List[float]] = {}

#     def get_model_price(self, model_name: str) -> str:
#         prices = self.AVAILABLE_MODELS.get(model_name, [0.0, 0.0])
#         return (
#             f"Model: {model_name}\n"
#             f"Input Price (/M Tokens): ${prices[0]:.2f}\n"
#             f"Output Price (/M Tokens): ${prices[1]:.2f}"
#         )


class CohereConfig:
    AVAILABLE_MODELS = {
        "command-r-08-2024": [0.30, 1.20],
        "command-r-plus-04-2024": [3.00, 15.00],
        "command-r-plus-08-2024": [2.50, 10.00],
        "command-r7b-12-2024": [0.0375, 0.15],
        "command-r-03-2024": [0.50, 1.50],
        "command-a-03-2025": [2.50, 10.00],
    }
