from typing import Any

import httpx
from eliot import start_action

from ensembl_mcp.config import Settings, get_settings


class GraphQLError(RuntimeError):
    """Raised when the Ensembl GraphQL endpoint returns an ``errors`` payload."""


class EnsemblGraphQLClient:
    """Thin async client for the Ensembl beta GraphQL API."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    @property
    def endpoint(self) -> str:
        return self._settings.endpoint

    async def execute(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
        endpoint: str | None = None,
    ) -> dict[str, Any]:
        """Run a GraphQL query and return the ``data`` object.

        Raises ``GraphQLError`` if the server reports query errors, and lets
        ``httpx.HTTPError`` propagate on transport/HTTP failures.
        """
        url = endpoint or self._settings.endpoint
        payload: dict[str, Any] = {"query": query}
        if variables:
            payload["variables"] = variables

        with start_action(
            action_type="ensembl_graphql_request",
            endpoint=url,
            has_variables=bool(variables),
        ) as action:
            async with httpx.AsyncClient(timeout=self._settings.request_timeout) as http:
                response = await http.post(url, json=payload)

            # Non-JSON responses (e.g. an HTML 500 error page) cannot carry a
            # GraphQL error body, so surface them as plain HTTP errors.
            if "json" not in response.headers.get("content-type", ""):
                response.raise_for_status()
                return {}

            body: dict[str, Any] = response.json()
            errors = body.get("errors")
            data = body.get("data")

            # The Ensembl API reports "not found" lookups as an error alongside a
            # null data field; we treat any present data as a usable result and
            # only fail when there is no data to return at all.
            if data is None:
                if errors:
                    messages = "; ".join(
                        error.get("message", "unknown error") for error in errors
                    )
                    raise GraphQLError(messages)
                response.raise_for_status()
                return {}

            action.add_success_fields(
                returned_keys=sorted(data.keys()), had_errors=bool(errors)
            )
            return data
