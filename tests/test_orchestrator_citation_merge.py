from app.orchestrator import ResearchOrchestrator


def test_merge_citation_results_handles_malformed_entries():
    orchestrator = ResearchOrchestrator.__new__(ResearchOrchestrator)

    primary = {
        "style": "IEEE",
        "citations": [
            {
                "number": 1,
                "formatted": "[1] Example source A",
                "doi": "10.1000/a",
                "paper": {"title": "Example Source A", "doi": "10.1000/a"},
            },
            ["invalid nested list"],
            "invalid string",
        ],
    }
    secondary = {
        "citations": [
            {
                "number": 1,
                "formatted": "[1] Duplicate source A",
                "doi": "10.1000/a",
                "paper": {"title": "Example Source A", "doi": "10.1000/a"},
            },
            {
                "number": 2,
                "formatted": "[2] Example source B",
                "paper": {"title": "Example Source B"},
            },
        ]
    }

    merged = ResearchOrchestrator._merge_citation_results(orchestrator, primary, secondary, target=30)

    assert merged["total"] == 2
    assert merged["citations"][0]["number"] == 1
    assert merged["citations"][1]["number"] == 2
    assert merged["citations"][0]["formatted"].startswith("[1]")
    assert merged["citations"][1]["formatted"].startswith("[2]")
