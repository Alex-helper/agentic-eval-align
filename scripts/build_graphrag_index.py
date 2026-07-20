from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KG = ROOT / "data" / "knowledge_graph" / "api_docs.json"
OUT = ROOT / "data" / "graphrag_index" / "index.json"


def main() -> None:
    graph = json.loads(KG.read_text(encoding="utf-8"))
    communities = {}
    for node in graph["nodes"]:
        community = node["tags"][0] if node.get("tags") else "general"
        node["community"] = community
        communities.setdefault(community, []).append(node["title"])
    index = {
        "nodes": graph["nodes"],
        "communities": [
            {"name": name, "summary": f"Local+Global Search community containing: {', '.join(titles)}"}
            for name, titles in communities.items()
        ],
        "edges": graph.get("edges", []),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
