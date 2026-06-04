from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_ENDPOINT = "https://beta.ensembl.org/data/graphql/core"

HUMAN_GENOME_ID = "a7335667-93e7-11ec-a39d-005056b38ce3"

load_dotenv()


class Settings(BaseSettings):
    """Runtime configuration for the Ensembl GraphQL MCP server.

    Values can be overridden via ``ENSEMBL_MCP_*`` environment variables or a
    local ``.env`` file.
    """

    model_config = SettingsConfigDict(
        env_prefix="ENSEMBL_MCP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    endpoint: str = Field(
        default=DEFAULT_ENDPOINT,
        description="Base Ensembl GraphQL endpoint used for all queries.",
    )
    request_timeout: float = Field(
        default=60.0,
        description=(
            "HTTP timeout in seconds. Kept generous because some Ensembl beta "
            "queries (e.g. genome keyword search) can be slow."
        ),
    )
    human_genome_id: str = Field(
        default=HUMAN_GENOME_ID,
        description="Genome id for the human reference assembly (GRCh38).",
    )
    agent_api_key: str | None = Field(
        default=None,
        description="API key used by the optional Agno natural-language agent.",
    )
    agent_model_id: str = Field(
        default="gpt-4o-mini",
        description="OpenAI-compatible model id used by the optional Agno agent.",
    )
    agent_base_url: str | None = Field(
        default=None,
        description="Optional OpenAI-compatible base URL for the Agno agent model.",
    )
    agent_timeout: float = Field(
        default=120.0,
        description="HTTP timeout in seconds for Agno model calls.",
    )


def get_settings() -> Settings:
    return Settings()
