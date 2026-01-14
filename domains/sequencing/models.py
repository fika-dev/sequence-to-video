from pydantic import BaseModel


class SequenceMetadata(BaseModel):
    locale: str = "en-US"
    context: str = ""
    title: str = "Untitled"
