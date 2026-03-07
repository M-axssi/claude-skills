#!/usr/bin/env python3
"""
papers_cli.py - Database CLI for the paper search system.

Subcommands:
  list [args]                          - Display formatted paper list
  context --direction DIR              - Get search context (last_date + existing_titles)
  save --direction DIR --type TYPE     - Save papers from stdin to db + update tracker

Usage examples:
  python papers_cli.py list
  python papers_cli.py list "3D generation"
  python papers_cli.py list "3D generation" track
  python papers_cli.py context --direction "3D generation"
  echo '[{...}]' | python papers_cli.py save --direction "3D generation" --type track
"""

import argparse
import io
import json
import re
import sys
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from pathlib import Path

# Force UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
else:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

CONFIG_PATH = "D:/claude-skills/paper_search/config.json"


# ── Shared utilities ──────────────────────────────────────────────────────────

def get_data_dir() -> str:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)["data_dir"]


def load_json(path: str, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default if default is not None else {}


def save_json(path: str, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def normalize_title(title: str) -> str:
    t = title.lower().strip()
    if ":" in t:
        t = t[: t.index(":")]
    return re.sub(r"[^\w\s]", "", t).strip()


def fuzzy_match(query: str, candidates: list) -> str | None:
    """Return best matching candidate. Returns None if no good match found."""
    q = query.lower()
    for c in candidates:
        if c.lower() == q:
            return c
    for c in candidates:
        if q in c.lower() or c.lower() in q:
            return c
    best, best_score = None, 0.0
    for c in candidates:
        score = SequenceMatcher(None, q, c.lower()).ratio()
        if score > best_score:
            best, best_score = c, score
    return best if best_score >= 0.5 else None


# ── list subcommand ───────────────────────────────────────────────────────────

def cmd_list(args_str: str):
    data_dir = get_data_dir()
    db = load_json(f"{data_dir}/papers_db.json", {})
    tracker = load_json(f"{data_dir}/paper_tracker_state.json", {})

    if not db:
        print("论文库为空，请先使用 /track-papers 或 /survey-papers 添加论文。")
        return

    # Parse args_str: "" | "<direction>" | "<direction> track|survey"
    parts = args_str.strip().split()
    type_filter = None
    if parts and parts[-1].lower() in ("track", "survey"):
        type_filter = parts.pop().lower()
    direction_query = " ".join(parts).strip()

    # Overview mode
    if not direction_query:
        total = sum(len(v) for v in db.values())
        print("## 论文索引概览\n")
        header = f"{'研究方向':<32} {'论文数':>6}  {'最后查询':>12}"
        print(header)
        print("-" * len(header))
        for direction, papers in db.items():
            last = tracker.get(direction, "—")
            print(f"{direction:<32} {len(papers):>5}篇  {last:>12}")
        print(f"\n共 {len(db)} 个方向，{total} 篇论文")
        print("\n提示：使用 `/list-papers <方向>` 查看某方向的详细论文列表。")
        return

    # Direction-specific mode
    matched = fuzzy_match(direction_query, list(db.keys()))
    if not matched:
        print(f"未找到方向「{direction_query}」，当前已有方向：")
        for d in db:
            print(f"  - {d}")
        return

    all_papers = db[matched]
    if type_filter:
        all_papers = [p for p in all_papers if p.get("type") == type_filter]

    track_papers = [p for p in all_papers if p.get("type") == "track"]
    survey_papers = [p for p in all_papers if p.get("type") == "survey"]

    total_all = len(db[matched])
    print(f"## {matched} 论文列表")
    print(f"**共 {len(all_papers)} 篇**（追踪: {len([p for p in db[matched] if p.get('type')=='track'])}篇"
          f" | 调研: {len([p for p in db[matched] if p.get('type')=='survey'])}篇）\n")

    def print_group(papers, label, sort_key):
        if not papers:
            return
        sorted_papers = sorted(papers, key=lambda p: p.get(sort_key, ""), reverse=True)
        print(f"--- {label} ---\n")
        print("| # | 论文 | 作者 | 日期 | 发表于 | 摘要 |")
        print("|---|------|------|------|--------|------|")
        for i, p in enumerate(sorted_papers, 1):
            authors = p.get("authors", [])
            author_str = "、".join(authors[:2]) + ("等" if len(authors) > 2 else "")
            venue = p.get("venue") or (f"arXiv:{p['arxiv_id']}" if p.get("arxiv_id") else "arXiv")
            summary = p.get("summary", "")
            if len(summary) > 60:
                summary = summary[:60] + "…"
            print(f"| {i} | **{p['title']}** | {author_str} | {p.get('date', '—')} | {venue} | {summary} |")
        print()

    if type_filter == "track":
        print_group(track_papers, "追踪论文（按时间倒序）", "found_at")
    elif type_filter == "survey":
        print_group(survey_papers, "调研论文（按日期倒序）", "date")
    else:
        print_group(track_papers, "追踪论文（按时间倒序）", "found_at")
        print_group(survey_papers, "调研论文（按日期倒序）", "date")


# ── context subcommand ────────────────────────────────────────────────────────

def cmd_context(direction: str):
    data_dir = get_data_dir()
    tracker = load_json(f"{data_dir}/paper_tracker_state.json", {})
    db = load_json(f"{data_dir}/papers_db.json", {})

    matched_tracker = fuzzy_match(direction, list(tracker.keys())) if tracker else None
    if matched_tracker:
        last_date = tracker[matched_tracker]
    else:
        last_date = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")

    matched_db = fuzzy_match(direction, list(db.keys())) if db else None
    existing_titles = [p["title"] for p in db.get(matched_db, [])] if matched_db else []

    print(json.dumps({
        "direction": direction,
        "matched_tracker": matched_tracker,
        "matched_db": matched_db,
        "last_date": last_date,
        "existing_titles": existing_titles,
        "existing_count": len(existing_titles),
    }, ensure_ascii=False, indent=2))


# ── save subcommand ───────────────────────────────────────────────────────────

def cmd_save(direction: str, paper_type: str):
    data_dir = get_data_dir()
    data = json.load(sys.stdin)
    new_papers = data if isinstance(data, list) else data.get("papers", [])

    db_path = f"{data_dir}/papers_db.json"
    db = load_json(db_path, {})

    matched = fuzzy_match(direction, list(db.keys())) if db else None
    key = matched or direction
    existing = db.get(key, [])
    existing_norms = {normalize_title(p["title"]) for p in existing}

    today = datetime.now().strftime("%Y-%m-%d")
    added = []
    for p in new_papers:
        norm = normalize_title(p.get("title", ""))
        if norm and norm not in existing_norms:
            p.setdefault("type", paper_type)
            p.setdefault("found_at", today)
            existing.append(p)
            added.append(p["title"])
            existing_norms.add(norm)

    db[key] = existing
    save_json(db_path, db)

    # Update tracker for track-type saves
    if paper_type == "track":
        tracker_path = f"{data_dir}/paper_tracker_state.json"
        tracker = load_json(tracker_path, {})
        tracker[key] = today
        save_json(tracker_path, tracker)

    print(json.dumps({
        "direction": key,
        "added": len(added),
        "added_titles": added,
        "total_in_direction": len(db[key]),
        "tracker_updated": paper_type == "track",
        "date": today,
    }, ensure_ascii=False, indent=2))


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "list":
        args_str = " ".join(sys.argv[2:])
        cmd_list(args_str)

    elif cmd == "context":
        parser = argparse.ArgumentParser()
        parser.add_argument("--direction", required=True)
        args = parser.parse_args(sys.argv[2:])
        cmd_context(args.direction)

    elif cmd == "save":
        parser = argparse.ArgumentParser()
        parser.add_argument("--direction", required=True)
        parser.add_argument("--type", dest="paper_type", required=True,
                            choices=["track", "survey"])
        args = parser.parse_args(sys.argv[2:])
        cmd_save(args.direction, args.paper_type)

    else:
        print(f"未知命令: {cmd}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
