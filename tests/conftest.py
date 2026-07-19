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


@pytest.fixture(scope="session")
def network_error(settings: Settings) -> str | None:
    """Probe the live core endpoint once and return an error message if offline."""
    try:
        response = httpx.post(
            settings.endpoint,
            json={"query": "{ version { api { major } } }"},
            timeout=15.0,
        )
        response.raise_for_status()
    except httpx.HTTPError as error:
        return str(error)
    return None


@pytest.fixture(autouse=True)
def require_network(request: pytest.FixtureRequest, network_error: str | None) -> None:
    """Skip integration tests when Ensembl is unreachable; keep pure tests runnable."""
    if request.node.get_closest_marker("integration") and network_error:
        pytest.skip(f"Ensembl GraphQL endpoint unreachable: {network_error}")
