"""Rule-based semantic classification of IfcSpaces (method = rule_based).

Scope (private candidate vs shared) is derived from the *composition* of each name-prefix
group (does it contain dwelling-signature rooms?) rather than from a fixed list of names.
"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

CLASSES = ["private_apartment_space", "common_circulation", "entrance", "technical_service", "storage",
           "parking", "foundation", "roof", "unknown"]


def parse_space_name(name: str | None, pattern: str) -> dict[str, Any] | None:
    if not name:
        return None
    m = re.match(pattern, name.strip())
    if not m:
        return None
    prefix, number, seq = m.group("prefix"), m.group("number"), m.group("seq")
    return {"prefix": prefix, "number": int(number), "seq": int(seq), "group_key": f"{prefix}{int(number)}"}


def _tokens(*texts: str | None) -> list[str]:
    out: list[str] = []
    for t in texts:
        if t:
            out += [x for x in re.split(r"[^a-z0-9]+", t.lower()) if x]
    return out


def _match(tokens: list[str], words: list[str]) -> list[str]:
    hits = []
    for w in words:
        for t in tokens:
            if (len(w) < 4 and t == w) or (len(w) >= 4 and t.startswith(w)):
                hits.append(w)
                break
    return hits


def function_of(name: str | None, long_name: str | None, lex: dict[str, list[str]]) -> tuple[str, list[str]]:
    toks = _tokens(long_name, name) if long_name else _tokens(name)
    # long_name preferred; for Schependomlaan-like files the room type lives in LongName
    for func, key in (("parking", "parking"), ("technical", "technical"), ("storage", "storage"),
                      ("circulation", "circulation"), ("entrance", "entrance"),
                      ("dwelling_room", "dwelling_signature"), ("sanitary", "sanitary"), ("unnamed", "unnamed")):
        hits = _match(toks, lex[key])
        if hits:
            return func, hits
    return "unknown", []


def _storey_cue(storey_name: str | None, cues: dict[str, list[str]]) -> str | None:
    toks = _tokens(storey_name)
    for cls, words in cues.items():
        if _match(toks, words):
            return cls
    return None


def classify_spaces(graph: dict[str, Any], rules: dict) -> dict[str, Any]:
    pat = rules["space_name"]["pattern"]
    lex = rules["lexicon"]
    min_sig = rules["grouping"]["min_dwelling_signature_types"]
    storeys = {s["global_id"]: s for s in graph["storeys"]}

    # 1) group composition
    comp: dict[str, set[str]] = defaultdict(set)
    parsed_by_id = {}
    func_by_id = {}
    for sp in graph["spaces"]:
        p = parse_space_name(sp["name"], pat)
        parsed_by_id[sp["global_id"]] = p
        f, hits = function_of(sp["name"], sp["long_name"] or sp.get("description"), lex)
        func_by_id[sp["global_id"]] = (f, hits)
    # The room type often sits in the Name itself ("3.04 keuken" splits on space) or in LongName.
    for sp in graph["spaces"]:
        p = parsed_by_id[sp["global_id"]]
        if p:
            f, hits = func_by_id[sp["global_id"]]
            if f in ("dwelling_room", "sanitary"):
                comp[p["group_key"]].update(h for h in hits if h in lex["dwelling_signature"])
    group_scope = {}
    for sp in graph["spaces"]:
        p = parsed_by_id[sp["global_id"]]
        if p and p["group_key"] not in group_scope:
            n = len(comp.get(p["group_key"], set()))
            group_scope[p["group_key"]] = {
                "scope": "private_candidate" if n >= min_sig else "shared",
                "dwelling_signature_types": sorted(comp.get(p["group_key"], set())),
                "alpha_prefix": p["prefix"],
            }

    out = []
    for sp in graph["spaces"]:
        gid = sp["global_id"]
        p = parsed_by_id[gid]
        f, hits = func_by_id[gid]
        st = storeys.get(sp["storey_id"])
        ev: list[dict[str, Any]] = []
        cue = _storey_cue(st["name"] if st else None, rules["storey_cues"])
        scope = "unknown"
        if p:
            g = group_scope[p["group_key"]]
            scope = g["scope"]
            ev.append({"signal": "name_prefix_group", "value": p["group_key"],
                       "detail": f"group has dwelling-signature types {g['dwelling_signature_types']}"})
        else:
            ev.append({"signal": "name_pattern", "value": None, "detail": "name does not match grouping pattern"})
        if hits:
            ev.append({"signal": "room_type_lexicon", "value": f, "detail": hits})
        if cue:
            ev.append({"signal": "storey_name_cue", "value": cue, "detail": st["name"] if st else None})
        if sp.get("zones"):
            ev.append({"signal": "ifc_zone", "value": sp["zones"], "detail": None})

        if cue in ("foundation", "roof", "parking"):
            cls = cue
        elif scope == "private_candidate":
            cls = "private_apartment_space"
        else:
            cls = {"parking": "parking", "technical": "technical_service", "storage": "storage",
                   "circulation": "common_circulation", "entrance": "entrance"}.get(f, "unknown")
        # a shared group's unnamed room stays unknown; a private group's unnamed room stays private
        conf = 0.5 + 0.2 * bool(p) + 0.15 * bool(hits) + 0.1 * bool(st)
        out.append({
            "space_global_id": gid, "space_name": sp["name"], "long_name": sp["long_name"],
            "storey_id": sp["storey_id"], "storey_name": st["name"] if st else None,
            "prefix_group": p["group_key"] if p else None,
            "group_scope": scope, "classification": cls, "function": f,
            "confidence": round(min(conf, 0.95), 2), "method": "rule_based", "model_status": "not_trained",
            "evidence": ev,
        })
    counts: dict[str, int] = defaultdict(int)
    for o in out:
        counts[o["classification"]] += 1
    return {
        "method": "rule_based", "model_status": "not_trained", "source_mode": graph["source_mode"],
        "classes": CLASSES, "space_count": len(out), "class_counts": dict(counts),
        "group_scopes": group_scope, "spaces": out,
    }
