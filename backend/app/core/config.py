from pydantic import BaseModel


class Settings(BaseModel):
    """Central place for engine settings; secrets belong in environment variables."""

    app_name: str = "OPAL Research Engine"
    api_version: str = "0.1.0"


settings = Settings()
