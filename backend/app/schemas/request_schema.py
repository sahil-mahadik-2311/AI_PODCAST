from pydantic import BaseModel
from typing import Optional

class GenerateRequest(BaseModel):
    name: str
    voice_agent: Optional[str] = None
