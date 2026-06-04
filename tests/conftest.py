import httpx
import pytest

from ensembl_mcp.client import EnsemblGraphQLClient
from ensembl_mcp.config import HUMAN_GENOME_ID, Settings


@pytest.fixture(scope="session")
def settings() -> Settings:
    return Settings()


@pytest.fixture(scope="session")
def client(settings: Settings) -> EnsemblGraphQLClient:
    return EnsemblGraphQLClient(settings)


@pytest.fixture(scope="session")
def human_genome_id() -> str:
    return HUMAN_GENOME_ID


@pytest.fixture(scope="session", autouse=True)
def require_network(settings: Settings) -> None:
    """Skip the whole integration suite if the live endpoint is unreachable."""
    try:
        response = httpx.post(
            settings.endpoint,
            json={"query": "{ version { api { major } } }"},
            timeout=15.0,
        )
        response.raise_for_status()
    except httpx.HTTPError as error:
        pytest.skip(f"Ensembl GraphQL endpoint unreachable: {error}")
