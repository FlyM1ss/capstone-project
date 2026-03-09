from app.core.database import get_db

# Re-export; central place for dependency injection
get_db_session = get_db
