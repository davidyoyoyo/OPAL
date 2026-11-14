import pytest

from app.sources.providers.eurostat_data import EurostatDataClient


def sample_jsonstat():
    return {
        "id": ["geo", "time"],
        "size": [2, 2],
        "dimension": {
            "geo": {"category": {"index": {"RO": 0, "DE": 1}}},
            "time": {"category": {"index": {"2023": 0, "2024": 1}}},
        },
        "value": [10.5, 11.5, 20.5, 21.5],
        "status": {"3": "p"},
    }


def test_jsonstat_is_expanded_into_dimensioned_observations():
    rows = EurostatDataClient.parse_jsonstat(sample_jsonstat())
    assert len(rows) == 4
    assert rows[0] == {
        "dimensions": {"geo": "RO", "time": "2023"},
        "value": 10.5,
        "status": None,
    }
    assert rows[3] == {
        "dimensions": {"geo": "DE", "time": "2024"},
        "value": 21.5,
        "status": "p",
    }


def test_jsonstat_sparse_values_preserve_missing_cells():
    payload = sample_jsonstat()
    payload["value"] = {"0": 10.5, "3": 21.5}
    rows = EurostatDataClient.parse_jsonstat(payload)
    assert [row["value"] for row in rows] == [10.5, None, None, 21.5]


def test_jsonstat_rejects_responses_over_configured_cell_limit():
    with pytest.raises(ValueError, match="exceeding"):
        EurostatDataClient.parse_jsonstat(sample_jsonstat(), max_observations=3)


def test_jsonstat_rejects_inconsistent_dimension_metadata():
    payload = sample_jsonstat()
    payload["size"] = [3, 2]
    with pytest.raises(ValueError, match="Category count"):
        EurostatDataClient.parse_jsonstat(payload)


@pytest.mark.parametrize(
    ("dataset_code", "filters", "message"),
    [
        ("../bad", {"geo": "RO"}, "dataset code"),
        ("demo", {}, "dimension filter"),
    ],
)
def test_fetch_requires_safe_dataset_and_bounded_filters(dataset_code, filters, message):
    import asyncio

    client = EurostatDataClient()
    with pytest.raises(ValueError, match=message):
        asyncio.run(client.fetch_observations(dataset_code, filters))
