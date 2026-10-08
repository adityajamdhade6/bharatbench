import json

import pytest

from bharatbench.tasks import load_tasks, resolve_categories
from fakes import make_task


def write(tmp_path, tasks, name="t.jsonl"):
    (tmp_path / name).write_text("\n".join(json.dumps(t) for t in tasks), encoding="utf-8")


def test_only_verified_tasks_are_loaded(tmp_path):
    write(tmp_path, [make_task("gst-001"), make_task("gst-002", verified=False)])
    assert [t["id"] for t in load_tasks(tmp_path)] == ["gst-001"]


def test_verified_only_can_be_disabled(tmp_path):
    write(tmp_path, [make_task("gst-001"), make_task("gst-002", verified=False)])
    assert len(load_tasks(tmp_path, verified_only=False)) == 2


def test_category_filter_and_aliases(tmp_path):
    write(tmp_path, [make_task("gst-001"), make_task("law-001", "law_policy"),
                     make_task("pay-001", "payments_banking")])
    assert [t["id"] for t in load_tasks(tmp_path, ["gst", "law"])] == ["gst-001", "law-001"]
    assert resolve_categories(["Hinglish", "hinglish_support", "docs"]) == ["hinglish_support", "documents"]


def test_unknown_category_raises(tmp_path):
    with pytest.raises(ValueError, match="unknown category"):
        resolve_categories(["cricket"])


def test_limit_is_per_category(tmp_path):
    write(tmp_path, [make_task(f"gst-00{i}") for i in range(1, 4)]
          + [make_task(f"law-00{i}", "law_policy") for i in range(1, 4)])
    ids = [t["id"] for t in load_tasks(tmp_path, limit_per_category=2)]
    assert ids == ["gst-001", "gst-002", "law-001", "law-002"]
