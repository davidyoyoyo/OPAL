from app.services.synthesis import build_extractive_synthesis


def test_extracts_result_sentences_across_studies_not_first_sentences():
    findings = [
        {
            "id": "study-1",
            "source_title": "Study one",
            "source_url": "https://example.com/1",
            "evidence_text": (
                "This study examines attitudes toward public transport in cities. "
                "Respondents who had access to reliable buses reported significantly "
                "higher satisfaction with local transport services."
            ),
        },
        {
            "id": "study-2",
            "source_title": "Study two",
            "source_url": "https://example.com/2",
            "evidence_text": (
                "The paper investigates commuting preferences among adults. "
                "Travel time was associated with reported satisfaction, while "
                "service frequency showed a stronger relationship in rural areas."
            ),
        },
    ]

    result = build_extractive_synthesis("public transport satisfaction", findings)

    assert result["mode"] == "extractive_fallback"
    assert len(result["key_points"]) >= 2
    assert all(point["source_ids"] for point in result["key_points"])
    assert all(
        not point["text"].startswith(("This study examines", "The paper investigates"))
        for point in result["key_points"]
    )
    assert "not a pooled estimate" in result["overview"]


def test_empty_findings_produce_transparent_overview():
    result = build_extractive_synthesis("public opinion", [])
    assert result["key_points"] == []
    assert "0 relevant scholarly records" in result["overview"]
