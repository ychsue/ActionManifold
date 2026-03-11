from typing import Any

from typing_extensions import TypedDict, NotRequired

class MyOutputSchema(TypedDict):
    status: str
    result: NotRequired[int]

class CtxWrite(TypedDict):
    mode: str            # "local" | "nearest" | "root"
    key: str
    to: NotRequired[Any]

class MyMetadataSchema(TypedDict):
    user_id: NotRequired[str]
    attempt: NotRequired[int]
