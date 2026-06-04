import pytest

from ensembl_mcp import queries
from ensembl_mcp.client import EnsemblGraphQLClient, GraphQLError

pytestmark = pytest.mark.integration


async def test_version_query_returns_semver(client: EnsemblGraphQLClient) -> None:
    data = await client.execute(queries.VERSION_QUERY)
    api = data["version"]["api"]
    assert {"major", "minor", "patch"} <= api.keys()


async def test_raw_passthrough_runs_arbitrary_query(client: EnsemblGraphQLClient) -> None:
    data = await client.execute("{ version { api { major } } }")
    assert "version" in data


async def test_graphql_errors_raise(client: EnsemblGraphQLClient) -> None:
    with pytest.raises(GraphQLError):
        await client.execute("{ this_field_does_not_exist }")
