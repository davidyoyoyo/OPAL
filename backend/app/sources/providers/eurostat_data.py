from itertools import product
import re
from typing import Any

import httpx


class EurostatDataClient:
    """Fetch bounded, filtered Eurostat observations in JSON-stat 2.0 format."""

    base_url = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"

    def __init__(self, timeout_seconds: float = 30.0) -> None:
        self.timeout_seconds = timeout_seconds

    @staticmethod
    def parse_jsonstat(
        payload: dict[str, Any], *, max_observations: int = 2000
    ) -> list[dict[str, Any]]:
        if not isinstance(payload, dict) or not isinstance(payload.get("dimension"), dict):
            raise ValueError("Eurostat returned an unexpected JSON-stat response.")
        dimensions = payload["dimension"]
        dimension_ids = payload.get("id", list(dimensions))
        sizes = payload.get("size", [])
        if len(dimension_ids) != len(sizes) or len(sizes) != len(dimensions):
            raise ValueError("Eurostat response has inconsistent dimension metadata.")

        total_cells = 1
        for size in sizes:
            total_cells *= int(size)
        if total_cells > max_observations:
            raise ValueError(
                f"Eurostat response contains {total_cells} cells, exceeding the "
                f"configured limit of {max_observations}. Narrow the dimension filters."
            )

        categories: list[list[str]] = []
        for dimension_id in dimension_ids:
            dimension = dimensions.get(dimension_id, {})
            index = dimension.get("category", {}).get("index", {})
            if isinstance(index, list):
                ordered_codes = [str(code) for code in index]
            elif isinstance(index, dict):
                ordered_codes = [
                    str(code) for code, _ in sorted(index.items(), key=lambda pair: pair[1])
                ]
            else:
                raise ValueError(f"Missing category index for dimension {dimension_id}.")
            if len(ordered_codes) != int(sizes[len(categories)]):
                raise ValueError(f"Category count does not match size for dimension {dimension_id}.")
            categories.append(ordered_codes)

        values = payload.get("value", [])
        statuses = payload.get("status", {})
        if not isinstance(values, (dict, list)):
            raise ValueError("Eurostat response has an unsupported value representation.")

        strides: list[int] = []
        for position in range(len(sizes)):
            stride = 1
            for later_size in sizes[position + 1:]:
                stride *= int(later_size)
            strides.append(stride)

        observations: list[dict[str, Any]] = []
        for coordinates in product(*(range(int(size)) for size in sizes)):
            flat_index = sum(
                coordinate * stride for coordinate, stride in zip(coordinates, strides)
            )
            value = (
                values.get(str(flat_index))
                if isinstance(values, dict)
                else values[flat_index] if flat_index < len(values) else None
            )
            dimension_values = {
                dimension_ids[position]: categories[position][coordinate]
                for position, coordinate in enumerate(coordinates)
            }
            observations.append({
                "dimensions": dimension_values,
                "value": value,
                "status": statuses.get(str(flat_index)) if isinstance(statuses, dict) else None,
            })
        return observations

    async def fetch_observations(
        self,
        dataset_code: str,
        filters: dict[str, str],
        *,
        max_observations: int = 2000,
    ) -> list[dict[str, Any]]:
        if not re.fullmatch(r"[A-Za-z0-9_]+", dataset_code):
            raise ValueError("Invalid Eurostat dataset code.")
        if not filters:
            raise ValueError("At least one dimension filter is required to bound the dataset request.")
        if not 1 <= max_observations <= 5000:
            raise ValueError("max_observations must be between 1 and 5000.")

        params = {"lang": "en", **filters}
        url = f"{self.base_url}/{dataset_code}"
        headers = {"User-Agent": "OPALResearch/0.3 (Eurostat statistical data)"}

        async with httpx.AsyncClient(timeout=self.timeout_seconds, headers=headers) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()

        return self.parse_jsonstat(payload, max_observations=max_observations)
