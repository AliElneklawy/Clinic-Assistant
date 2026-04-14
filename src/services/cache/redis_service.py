from typing import Any, Dict, List, Optional

from redisvl.extensions.cache.llm import SemanticCache
from redisvl.utils.vectorize import CohereTextVectorizer

from src.scripts import get_api_key
from src.services.cache.base_cache import BaseCache
from src.settings import cache_config
from src.settings.logger import get_logger
from src.settings.settings import settings

logger = get_logger(__name__)


class RedisService(BaseCache):
    def __init__(self, name: Optional[str]) -> None:
        self.cache = SemanticCache(
            name=name,
            distance_threshold=cache_config.DIST_THRESHOLD,
            redis_url=settings.REDIS_URL,
            ttl=cache_config.TTL,
            vectorizer=CohereTextVectorizer(  # See the note about initializing the vectorizer at the last line
                model=cache_config.EMBEDDER,
                api_config={"api_key": settings.COHERE},
            ),
        )

    def store(self, key, value, ttl=None) -> str:
        key = self.cache.store(prompt=key, response=value, ttl=ttl)
        return key

    def retrieve(
        self, key, num_results: int = 1, distance_threshold: float | None = None
    ) -> List[Dict[str, Any]]:
        result = self.cache.check(
            prompt=key, num_results=num_results, distance_threshold=distance_threshold
        )
        return result

    def delete(
        self,
        keys: List[str] | None = None,
        ids: List[str] | None = None,
        clr_cached_resp: bool = False,
        destroy_cache: bool = False,
    ) -> None:
        if destroy_cache:
            self.cache.delete()
        elif clr_cached_resp:
            self.cache.clear()
        else:
            self.cache.drop(keys=keys, ids=ids)

    def update(self, key, value=None):
        self.cache.update(key, response=value)

    def set_expiration(self, key: str, ttl: int | None = None) -> None:
        self.cache.expire(key=key, ttl=ttl)


# Regarding the initialization process of the vectorizer. I kept getting the following errors:
#   1. TypeError: Must pass in a str value for cohere embedding input_type. See https://docs.cohere.com/reference/embed
#   2. TypeError: Client.__init__() got an unexpected keyword argument 'input_type'
# The second error occured when I tried to pass the 'input_type' arg CohereTextVectorizer.
# So I had to change line 236 from
#                               `input_type = kwargs.pop("input_type", None)`
#                             to
#                               `input_type = kwargs.pop("input_type", "search_query")`
# in .venv\Lib\site-packages\redisvl\utils\vectorize\text\cohere.py
