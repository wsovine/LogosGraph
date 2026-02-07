"""Configuration and environment settings."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")


class Settings:
    """Application settings loaded from environment."""

    # Neo4j connection
    NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER: str = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "logosgraph")

    # Anthropic API (for LLM extraction)
    ANTHROPIC_API_KEY: str | None = os.getenv("ANTHROPIC_API_KEY")

    # Import settings
    BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", "5000"))

    # Data paths
    DATA_DIR: Path = PROJECT_ROOT / "data" / "raw"

    # Data source URLs
    CPDV_URL: str = "https://raw.githubusercontent.com/scrollmapper/bible_databases/master/sources/en/CPDV/CPDV.json"
    TSK_URL: str = "https://raw.githubusercontent.com/scrollmapper/bible_databases/master/sources/extras/cross_references.txt"
    HAYDOCK_ZIP_URL: str = "https://github.com/cmahte/ENG-B-Haydock1883-pd-PSFM/archive/refs/heads/master.zip"

    # Haydock directory (extracted from ZIP)
    HAYDOCK_DIR: Path = DATA_DIR / "haydock"


settings = Settings()