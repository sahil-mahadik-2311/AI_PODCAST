from pydantic import BaseModel
from typing import List, Optional

class GenerateResponse(BaseModel):
    date: str
    podcast_script: str
    audio_url: Optional[str]
    status: str
    error: Optional[str] = None