from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://deloitte:deloitte_dev@localhost:5432/search_engine"
    EMBEDDING_API_URL: str = "http://localhost:8001/embed"
    COHERE_API_KEY: str = ""
    GOTENBERG_URL: str = "http://localhost:3001"

    # Search tuning
    SEARCH_TOP_K: int = 50
    RERANK_TOP_N: int = 10
    RRF_K: int = 60
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 50
    TITLE_BOOST_WEIGHT: float = 1.5
    EMBED_BATCH_SIZE: int = 64

    class Config:
        env_file = ".env"


settings = Settings()
