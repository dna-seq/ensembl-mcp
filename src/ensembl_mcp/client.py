from pathlib import Path
from typing import Any

import httpx
from eliot import start_action

from ensembl_mcp.config import Settings, get_settings


class GraphQLError(RuntimeError):
    """Raised when the Ensembl GraphQL endpoint returns an ``errors`` payload."""


class EnsemblGraphQLTrait:
    """Trait providing Ensembl GraphQL query capabilities."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

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


class EnsemblRefgetTrait:
    """Trait providing GA4GH Refget sequence retrieval capabilities."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def refget_endpoint(self) -> str:
        return self._settings.refget_endpoint

    async def fetch_sequence(
        self,
        sequence_id: str,
        start: int | None = None,
        end: int | None = None,
    ) -> str:
        """Retrieve a sequence or subsequence from the Refget server."""
        url = f"{self.refget_endpoint}/sequence/{sequence_id}"
        params: dict[str, Any] = {}
        if start is not None:
            params["start"] = start
        if end is not None:
            params["end"] = end

        with start_action(
            action_type="ensembl_refget_sequence_request",
            endpoint=url,
            sequence_id=sequence_id,
            start=start,
            end=end,
        ):
            async with httpx.AsyncClient(timeout=self._settings.request_timeout) as http:
                response = await http.get(url, params=params)
                response.raise_for_status()
                return response.text

    async def fetch_sequence_to_file(
        self,
        sequence_id: str,
        output_path: Path,
        start: int | None = None,
        end: int | None = None,
    ) -> int:
        """Stream a sequence or subsequence from Refget to a local file."""
        url = f"{self.refget_endpoint}/sequence/{sequence_id}"
        params: dict[str, Any] = {}
        if start is not None:
            params["start"] = start
        if end is not None:
            params["end"] = end

        with start_action(
            action_type="ensembl_refget_sequence_file_request",
            endpoint=url,
            sequence_id=sequence_id,
            start=start,
            end=end,
            output_path=str(output_path),
        ):
            async with httpx.AsyncClient(timeout=self._settings.request_timeout) as http:
                async with http.stream("GET", url, params=params) as response:
                    response.raise_for_status()
                    bytes_written = 0
                    with output_path.open("wb") as output:
                        async for chunk in response.aiter_bytes():
                            bytes_written += len(chunk)
                            output.write(chunk)
                    return bytes_written

    async def fetch_sequence_metadata(self, sequence_id: str) -> dict[str, Any]:
        """Retrieve metadata for a sequence ID from the Refget server."""
        url = f"{self.refget_endpoint}/sequence/{sequence_id}/metadata"
        with start_action(
            action_type="ensembl_refget_metadata_request",
            endpoint=url,
            sequence_id=sequence_id,
        ):
            async with httpx.AsyncClient(timeout=self._settings.request_timeout) as http:
                response = await http.get(url)
                response.raise_for_status()
                return response.json()


class EnsemblGraphQLClient(EnsemblGraphQLTrait, EnsemblRefgetTrait):
    """Unified client combining both GraphQL and Refget capabilities."""

    def __init__(self, settings: Settings | None = None) -> None:
        settings = settings or get_settings()
        EnsemblGraphQLTrait.__init__(self, settings)
        EnsemblRefgetTrait.__init__(self, settings)
