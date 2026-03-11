import os
from typing import Any, Dict, List, Optional

from redisvl.extensions.cache.llm import SemanticCache
from redisvl.utils.vectorize import CohereTextVectorizer

from src.scripts import get_api_key
from src.services.cache.base_cache import BaseCache
from src.settings import cache_config
from src.settings.logger import get_logger

logger = get_logger(__name__)


class RedisService(BaseCache):
    def __init__(self, name: Optional[str]) -> None:
        self.cache = SemanticCache(
            name=name,
            distance_threshold=cache_config.DIST_THRESHOLD,
            redis_url=os.getenv("REDIS_URL"),
            ttl=cache_config.TTL,
            vectorizer=CohereTextVectorizer(  # See the note about initializing the vectorizer at the last line
                model=cache_config.EMBEDDER,
                api_config={"api_key": get_api_key.get_key("COHERE")},
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
