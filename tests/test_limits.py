import builtins
import io
import json
import os
import sys
from unittest.mock import AsyncMock, Mock
import pytest

import types

# Ensure repository root is on sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Provide dummy module for dependencies required by the workflow module
dummy_utils = types.ModuleType("utils.fba_calculator")
class DummyCalc:
    pass
dummy_utils.FBACalculator = DummyCalc
sys.modules["utils.fba_calculator"] = dummy_utils

import tools.passive_extraction_workflow_latest as wf

@pytest.mark.asyncio
async def test_run_workflow_main_passes_limits(monkeypatch):
    config_data = {"system": {"max_products_per_category": 3, "max_analyzed_products": 5, "max_products_per_cycle": 7}}

    config_json = json.dumps(config_data)

    orig_exists = os.path.exists
    def fake_exists(path):
        if path.endswith(os.path.join("config", "system_config.json")):
            return True
        return orig_exists(path)
    monkeypatch.setattr(os.path, "exists", fake_exists)

    orig_open = builtins.open
    def fake_open(path, *args, **kwargs):
        if path.endswith(os.path.join("config", "system_config.json")):
            return io.StringIO(config_json)
        return orig_open(path, *args, **kwargs)
    monkeypatch.setattr(builtins, "open", fake_open)

    mock_instance = Mock()
    mock_run = AsyncMock(return_value=[])
    mock_instance.run = mock_run
    monkeypatch.setattr(wf, "PassiveExtractionWorkflow", Mock(return_value=mock_instance))

    monkeypatch.setattr(sys, "argv", ["prog"])

    await wf.run_workflow_main()

    assert mock_run.call_count == 1
    kwargs = mock_run.call_args.kwargs
    assert kwargs["max_products_per_category"] == 3
    assert kwargs["max_analyzed_products"] == 5
    assert kwargs["max_products_to_process"] == 7


@pytest.mark.asyncio
async def test_run_respects_max_analyzed(monkeypatch):
    workflow = wf.PassiveExtractionWorkflow(chrome_debug_port=0, ai_client=None, max_cache_age_hours=1, min_price=0.1)

    async def fake_extract(*args, **kwargs):
        return [
            {"title": "p1", "price": 1.0, "url": "u1", "ean": "e1", "source_category_url": "cat1"},
            {"title": "p2", "price": 1.0, "url": "u2", "ean": "e2", "source_category_url": "cat1"},
            {"title": "p3", "price": 1.0, "url": "u3", "ean": "e3", "source_category_url": "cat2"},
        ]

    monkeypatch.setattr(workflow, "_extract_supplier_products", fake_extract)

    dummy_extractor = types.SimpleNamespace(
        search_by_ean_and_extract_data=AsyncMock(return_value={"asin": "A1", "title": "A", "current_price": 20, "keepa": {}}),
        search_by_title_using_search_bar=AsyncMock(return_value={"results": [{"asin": "A1"}]}),
        extract_data=AsyncMock(return_value={"title": "A", "current_price": 20, "keepa": {}}),
    )
    workflow.extractor = dummy_extractor

    monkeypatch.setattr(workflow, "_get_cached_amazon_data_by_asin", AsyncMock(return_value=None))
    monkeypatch.setattr(workflow, "_cache_amazon_data", AsyncMock())
    monkeypatch.setattr(workflow, "_validate_product_match", AsyncMock(return_value={"match_quality": "high", "confidence_score": 1.0}))
    monkeypatch.setattr(workflow, "_passes_quick_triage", Mock(return_value=True))
    monkeypatch.setattr(workflow, "_is_product_meeting_criteria", Mock(return_value=False))
    monkeypatch.setattr(workflow, "_should_trigger_new_ai_cycle", Mock(return_value=False))

    results = await workflow.run(
        supplier_url="url",
        supplier_name="name",
        max_products_to_process=10,
        max_products_per_category=0,
        max_analyzed_products=2,
        cache_supplier_data=False,
        resume_from_last=False,
    )

    assert workflow.results_summary["products_processed_total"] == 2
    assert sum(workflow.results_summary["products_processed_per_category"].values()) == 2
    assert results == []
