from fastapi import FastAPI
from app.config.metadata import (
    TITLE,
    SUMMARY,
    VERSION,
    DESCRIPTION,
    TAGS_METADATA
)

app = FastAPI(
    title=TITLE,
    summary=SUMMARY,
    version=VERSION,
    description=DESCRIPTION,
    openapi_tags=TAGS_METADATA
)

@app.get("/")
async def read_root():
    return {"message": "Hello, World!"}