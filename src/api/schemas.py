from typing import Annotated

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: Annotated[str, Field(..., description="User's message to the bot.")]
    user_id: Annotated[
        str | None,
        Field(None, description="A unique ID to persist chat history for each user."),
    ]


class UserInputDiabetes(BaseModel): ...
