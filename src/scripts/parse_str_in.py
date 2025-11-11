import ast
import re
from typing import Type, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def parse_to(arg_str: str, model: Type[T]) -> T:
    # Turn "a=1, b='x'" → "{'a':1, 'b':'x'}"
    cleaned = re.sub(r"(\w+)\s*=", r"'\1':", arg_str)
    cleaned = "{" + cleaned + "}"
    data = ast.literal_eval(cleaned)

    return model(**data)
