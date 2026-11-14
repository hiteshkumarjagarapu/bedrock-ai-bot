from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    file_type: str
    chunk_count: int
    created_at: datetime


class UploadResponse(BaseModel):
    document: DocumentResponse
    message: str
