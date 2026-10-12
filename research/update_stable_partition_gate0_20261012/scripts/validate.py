#!/usr/bin/env python3
"""Check this bounded literature record; scientific judgment remains manual."""
import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

root = Path(__file__).resolve().parents[1]
ship = [
    "README.md", "SEARCH_SCOPE.md", "PRIOR_ART_MATRIX.md", "EVIDENCE_CARDS.md",
    "NEAREST_WORK.md", "NOVELTY_DECISION.md", "NEXT_MECHANISM.md",
    "CLAIM_EVIDENCE.md", "PUBLICATION_GATE.md", "CONTRACT.json",
    "evidence/SOURCES.json", "evidence/CARDS.json", "evidence/DECISION.json",
    "scripts/validate.py",
]
contract = json.loads((root / "CONTRACT.json").read_text())
sources = json.loads((root / "evidence/SOURCES.json").read_text())["sources"]
cards = json.loads((root / "evidence/CARDS.json").read_text())
decision = json.loads((root / "evidence/DECISION.json").read_text())
ids = [s["id"] for s in sources]
assert len(ids) == len(set(ids)) == 15
assert sum(s["kind"] == "primary_paper" for s in sources) == 14
assert len(cards) == 15 and {c["id"] for c in cards} == set(ids)
assert contract["gpu_process_budget"] == decision["gpu_processes_started"] == 0
assert decision["decision"] == "KILL" and "unknown" in decision["kill_3"]
assert decision["implementation_status"] == "not implemented"
required = {
    "id", "family", "data_query_type", "exact_or_approximate", "insert", "delete",
    "partition_representation", "persistence", "repartition_trigger",
    "structural_instability", "explicit_stability_goal", "nearest_overlap",
    "key_difference", "novelty_risk", "material_caveat",
}
card_text = (root / "EVIDENCE_CARDS.md").read_text()
for card in cards:
    assert set(card) == required and all(isinstance(v, str) and v for v in card.values())
    assert card["novelty_risk"] in {"HIGH", "MEDIUM", "LOW"}
    assert "## " + card["id"] + " — " in card_text
    assert all(v in card_text for k, v in card.items() if k not in {"id", "family"})
for source in sources:
    assert urlsplit(source["url"]).scheme == "https"
    assert re.fullmatch(r"[0-9a-f]{64}", source["sha256"])
    assert source["bytes"] > 0 and source["checked_sections"]
    if source["kind"] == "primary_paper":
        assert all(1 <= p <= source["pdf_page_count"] for p in source["checked_pdf_pages_1_based"])
    else:
        assert re.fullmatch(r"[0-9a-f]{40}", source["commit"])
        assert source["commit"] in source["url"]
    if "--check-local-sources" in sys.argv:
        name = "ompl_gnat.h" if source["id"] == "ompl_gnat" else source["id"] + ".pdf"
        raw = (root / "local/sources" / name).read_bytes()
        assert len(raw) == source["bytes"]
        assert hashlib.sha256(raw).hexdigest() == source["sha256"]
for item in ship:
    text = (root / item).read_text()
    assert not re.search(r"/(?:Users|home)/|gh[pousr]_[A-Za-z0-9]{20,}", text)
    if item.endswith(".md"):
        for target in re.findall(r"\]\(([^)]+)\)", text):
            if not urlsplit(target).scheme:
                assert (root / target.split("#", 1)[0]).exists(), target
baseline = root.parent.parent / "diagnostics/l3_residual_attribution_20261012/summary/RESULT.json"
assert hashlib.sha256(baseline.read_bytes()).hexdigest() == contract["baseline_l3_result_sha256"]
assert all(x in ids for x in decision["decisive_sources"])
print("PASS: 14 papers + pinned code, 15 complete cards, links, baseline hash, scoped KILL, zero-GPU contract.")
if "--check-local-sources" in sys.argv:
    print("PASS: all 15 privately retained primary-source byte hashes.")
