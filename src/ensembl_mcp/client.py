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


class EnsemblRestTrait:
    """Trait providing JSON access to Ensembl REST services."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def fetch_rsid(self, species: str, rsid: str) -> dict[str, Any]:
        """Retrieve legacy Ensembl variation data used to map an rsID."""
        url = f"{self._settings.rest_endpoint}/variation/{species}/{rsid}"
        with start_action(
            action_type="ensembl_rest_variation_request",
            endpoint=url,
            species=species,
            rsid=rsid,
        ):
            async with httpx.AsyncClient(timeout=self._settings.request_timeout) as http:
                response = await http.get(
                    url,
                    headers={"Accept": "application/json"},
                )
                response.raise_for_status()
                return response.json()

    async def fetch_variations_at_coordinate(
        self, species: str, coordinate: str
    ) -> list[dict[str, Any]]:
        """Retrieve variations overlapping an exact ``region:position`` coordinate."""
        region, position = coordinate.split(":", maxsplit=1)
        interval = f"{region}:{position}-{position}"
        url = f"{self._settings.rest_endpoint}/overlap/region/{species}/{interval}"
        with start_action(
            action_type="ensembl_rest_coordinate_variations_request",
            endpoint=url,
            species=species,
            coordinate=coordinate,
        ):
            async with httpx.AsyncClient(timeout=self._settings.request_timeout) as http:
                response = await http.get(
                    url,
                    params={"feature": "variation"},
                    headers={"Accept": "application/json"},
                )
                response.raise_for_status()
                return response.json()

    async def fetch_variations_in_region(
        self,
        species: str,
        region: str,
        start: int,
        end: int,
        consequence_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve all variations overlapping a genomic interval."""
        interval = f"{region}:{start}-{end}"
        url = f"{self._settings.rest_endpoint}/overlap/region/{species}/{interval}"
        params: dict[str, Any] = {"feature": "variation"}
        if consequence_type:
            params["variant_set_id"] = consequence_type
        with start_action(
            action_type="ensembl_rest_region_variations_request",
            endpoint=url,
            species=species,
            interval=interval,
        ):
            async with httpx.AsyncClient(timeout=self._settings.request_timeout) as http:
                response = await http.get(
                    url,
                    params=params,
                    headers={"Accept": "application/json"},
                )
                response.raise_for_status()
                return response.json()

    async def fetch_phenotypes_for_gene(
        self,
        species: str,
        gene: str,
    ) -> list[dict[str, Any]]:
        """Retrieve phenotype associations for a gene symbol or Ensembl ID."""
        url = f"{self._settings.rest_endpoint}/phenotype/gene/{species}/{gene}"
        with start_action(
            action_type="ensembl_rest_gene_phenotypes_request",
            endpoint=url,
            species=species,
            gene=gene,
        ):
            async with httpx.AsyncClient(timeout=self._settings.request_timeout) as http:
                response = await http.get(
                    url,
                    headers={"Accept": "application/json"},
                )
                response.raise_for_status()
                return response.json()

    async def fetch_variant_recoder(
        self,
        species: str,
        variant_id: str,
    ) -> list[dict[str, Any]]:
        """Recode a variant between rsID, HGVS, SPDI, and VCF representations."""
        url = f"{self._settings.rest_endpoint}/variant_recoder/{species}/{variant_id}"
        with start_action(
            action_type="ensembl_rest_variant_recoder_request",
            endpoint=url,
            species=species,
            variant_id=variant_id,
        ):
            async with httpx.AsyncClient(timeout=self._settings.request_timeout) as http:
                response = await http.get(
                    url,
                    headers={"Accept": "application/json"},
                )
                response.raise_for_status()
                return response.json()

    async def fetch_releases(self) -> Any:
        """Retrieve release metadata from the Ensembl beta metadata API."""
        url = f"{self._settings.metadata_endpoint}/releases"
        with start_action(
            action_type="ensembl_metadata_releases_request",
            endpoint=url,
        ):
            async with httpx.AsyncClient(timeout=self._settings.request_timeout) as http:
                response = await http.get(
                    url,
                    headers={"Accept": "application/json"},
                )
                response.raise_for_status()
                return response.json()


class EnsemblGraphQLClient(
    EnsemblGraphQLTrait,
    EnsemblRefgetTrait,
    EnsemblRestTrait,
):
    """Unified client combining GraphQL, Refget, and REST capabilities."""

    def __init__(self, settings: Settings | None = None) -> None:
        settings = settings or get_settings()
        EnsemblGraphQLTrait.__init__(self, settings)
        EnsemblRefgetTrait.__init__(self, settings)
        EnsemblRestTrait.__init__(self, settings)
