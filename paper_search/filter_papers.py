#!/usr/bin/env python3
"""
filter_papers.py - Programmatic paper filtering to reduce LLM token usage.

Usage:
    echo '{"papers": [...], "existing_titles": [...]}' | python filter_papers.py

Input JSON:
    papers          - list of paper dicts from arXiv/Scholar MCP
    existing_titles - list of already-saved paper titles (for dedup)
    max_results     - max papers to return (default: 30)

Output JSON:
    filtered        - sorted, quality-filtered papers (ready to show user)
    needs_author_check - arXiv papers whose institution couldn't be matched
                         (LLM should call get_author_info for these)
    stats           - counts at each stage
"""

import json
import re
import sys
from typing import Dict, List

# ── Venue whitelist ───────────────────────────────────────────────────────────
TOP_VENUES = [
    "SIGGRAPH", "SIGGRAPH Asia", "ACM TOG", "IEEE TVCG",
    "Eurographics", "Pacific Graphics",
    "CVPR", "ICCV", "ECCV", "NeurIPS", "ICLR", "ICML", "AAAI",
    "ICRA", "IROS", "RSS", "RA-L", "IEEE Robotics",
    "3DV", "BMVC", "WACV", "IJCAI",
]

S_TIER = ["SIGGRAPH", "ACM TOG", "CVPR", "NeurIPS", "ICLR"]
A_TIER = ["ICCV", "ECCV", "SIGGRAPH Asia", "AAAI", "ICML"]

# ── Institution whitelist ─────────────────────────────────────────────────────
TOP_INSTITUTIONS = [
    "MIT", "Stanford", "CMU", "Carnegie Mellon", "Berkeley",
    "Oxford", "Cambridge", "ETH Zurich", "EPFL",
    "Google", "DeepMind", "Meta", "Facebook", "Microsoft",
    "Apple", "NVIDIA", "Adobe", "Amazon", "OpenAI", "Anthropic",
    "Tsinghua", "Peking University", "PKU", "SJTU", "Fudan",
    "Zhejiang University", "NJU", "NTU", "NUS",
    "KAIST", "POSTECH", "Tokyo", "Kyoto",
    "Tencent", "ByteDance", "Alibaba", "Baidu", "Huawei",
    "INRIA", "MPI", "Max Planck",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def normalize_title(title: str) -> str:
    """Lowercase + strip subtitle after colon + remove punctuation."""
    t = title.lower().strip()
    if ":" in t:
        t = t[: t.index(":")]
    return re.sub(r"[^\w\s]", "", t).strip()


def truncate_abstract(abstract: str, max_words: int = 30) -> str:
    if not abstract:
        return ""
    words = abstract.split()
    truncated = " ".join(words[:max_words])
    return truncated + ("..." if len(words) > max_words else "")


def check_venue(venue: str) -> bool:
    if not venue:
        return False
    v = venue.upper()
    return any(kw.upper() in v for kw in TOP_VENUES)


def check_institution(text: str) -> bool:
    if not text:
        return False
    t = text.upper()
    return any(inst.upper() in t for inst in TOP_INSTITUTIONS)


def venue_tier(venue: str) -> int:
    """1=S, 2=A, 3=other top, 4=not top."""
    if not venue:
        return 4
    v = venue.upper()
    if any(kw.upper() in v for kw in S_TIER):
        return 1
    if any(kw.upper() in v for kw in A_TIER):
        return 2
    if any(kw.upper() in v for kw in TOP_VENUES):
        return 3
    return 4


def sort_key(paper: Dict) -> tuple:
    title = paper.get("title", "").lower()
    is_survey = int(not ("survey" in title or "review" in title))  # 0=survey first
    vt = venue_tier(paper.get("venue", ""))
    st = paper.get("_source_tier", 4)
    return (is_survey, vt, st)


# ── Main ──────────────────────────────────────────────────────────────────────

def parse_date(s: str) -> str:
    """Extract YYYY-MM-DD prefix from various date formats, return '' if unparseable."""
    if not s:
        return ""
    # Take first 10 chars which should be YYYY-MM-DD
    return s[:10] if len(s) >= 10 else s


def filter_and_sort(
    papers: List[Dict],
    existing_titles: List[str] = None,
    max_results: int = 30,
    date_from: str = None,      # ISO date string YYYY-MM-DD; exclude papers before this
) -> Dict:
    existing_norm = {normalize_title(t) for t in (existing_titles or [])}

    # 1. Deduplicate by normalized title + exclude already-saved papers + date filter
    seen: set = set()
    unique: List[Dict] = []
    skipped_date = 0
    for p in papers:
        norm = normalize_title(p.get("title", ""))
        if norm and norm not in seen and norm not in existing_norm:
            # Date filter: skip papers published before date_from
            if date_from:
                pub = parse_date(p.get("published", "") or p.get("date", ""))
                if pub and pub < date_from:
                    skipped_date += 1
                    continue
            seen.add(norm)
            # Truncate abstract immediately to save tokens
            if "abstract" in p:
                p["abstract_short"] = truncate_abstract(p["abstract"])
                del p["abstract"]
            unique.append(p)

    # 2. Quality tier assignment
    tier1: List[Dict] = []   # top venue → include
    tier2: List[Dict] = []   # institution match → include
    tier3: List[Dict] = []   # unknown → needs get_author_info

    for p in unique:
        venue = p.get("venue", "")
        authors_text = " ".join(p.get("authors", []))
        hint_text = authors_text + " " + p.get("abstract_short", "")

        if check_venue(venue):
            p["_source_tier"] = 1
            tier1.append(p)
        elif check_institution(hint_text):
            p["_source_tier"] = 2
            tier2.append(p)
        else:
            p["_source_tier"] = 3
            tier3.append(p)

    # 3. Rule-based sort (surveys first, then S/A/B tier venues, then arXiv)
    combined = sorted(tier1 + tier2, key=sort_key)
    final = combined[:max_results]

    # Clean internal keys before output
    for p in final:
        p.pop("_source_tier", None)

    return {
        "filtered": final,
        "needs_author_check": tier3,
        "stats": {
            "total_input": len(papers),
            "skipped_before_date": skipped_date,
            "after_dedup_and_existing": len(unique),
            "tier1_top_venue": len(tier1),
            "tier2_institution": len(tier2),
            "tier3_needs_author_check": len(tier3),
            "final_selected": len(final),
        },
    }


if __name__ == "__main__":
    data = json.load(sys.stdin)
    result = filter_and_sort(
        papers=data.get("papers", []),
        existing_titles=data.get("existing_titles", []),
        max_results=data.get("max_results", 30),
        date_from=data.get("date_from"),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
