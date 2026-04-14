from typing import Type, TypeVar

from pydantic import BaseModel

from src.scripts.parse_str_in import parse_to

T = TypeVar("T", bound=BaseModel)


def unpack(data: str, model: Type[T]):
    parsed_data = parse_to(data.rstrip("O"), model)
    # return tuple(v for v in parsed_data.model_dump().values())
    return parsed_data
