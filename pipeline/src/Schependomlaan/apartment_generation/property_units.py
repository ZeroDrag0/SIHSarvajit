"""Derive candidate vertical property units from IFC evidence.

An IfcSpace is NOT a property unit.  Spaces are first grouped by evidence; only groups whose
composition looks like a dwelling (see classification) become *inferred prototype* units.
Evidence combined: name-prefix groups, storey membership, IfcZone / property-set membership
(when the file has them), geometric adjacency (when geometry exists), duplicate/gap analysis.
The unit count is whatever the evidence yields; it is only *compared* with any count declared
in the project name.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import Any

from shapely.geometry import shape
from shapely.ops import unary_union

from Schependomlaan.classification.space_classifier import parse_space_name

UNIT_CLASSIFICATION = "derived/inferred prototype property unit"


def _unit_id(group_key: str) -> str:
    m = re.match(r"^([A-Za-z]*)(\d+)$", group_key)
    return f"PU-{m.group(1)}{int(m.group(2)):02d}" if m else f"PU-{group_key}"


def _adjacent(a: dict, b: dict, tol: float, ztol: float = 0.05) -> bool:
    fa, fb = a.get("footprint"), b.get("footprint")
    if not fa or not fb:
        return False
    z_overlap = min(a["z_max"], b["z_max"]) - max(a["z_min"], b["z_min"])
    pa, pb = shape(fa), shape(fb)
    if z_overlap > ztol:
        return pa.distance(pb) <= tol
    gap = max(a["z_min"], b["z_min"]) - min(a["z_max"], b["z_max"])      # vertically stacked
    return gap <= 0.5 and pa.intersection(pb).area > 0.05


def _components(ids: list[str], geom: dict[str, dict], tol: float) -> list[list[str]]:
    seen, comps = set(), []
    for i in ids:
        if i in seen:
            continue
        stack, comp = [i], []
        while stack:
            x = stack.pop()
            if x in seen:
                continue
            seen.add(x)
            comp.append(x)
            stack += [y for y in ids if y not in seen and _adjacent(geom[x], geom[y], tol)]
        comps.append(comp)
    return comps


def _group_dist(sid: str, others: list[str], geom: dict[str, dict]) -> float | None:
    if sid not in geom or not geom[sid].get("footprint"):
        return None
    ds = [shape(geom[sid]["footprint"]).distance(shape(geom[o]["footprint"]))
          for o in others if o in geom and geom[o].get("footprint") and o != sid]
    return min(ds) if ds else None


def derive_property_units(graph: dict[str, Any], classification: dict[str, Any], rules: dict,
                          space_geom: dict[str, Any] | None = None) -> dict[str, Any]:
    gr = rules["grouping"]
    tol = gr["adjacency_tolerance_m"]
    pat = rules["space_name"]["pattern"]
    spaces = {s["global_id"]: s for s in graph["spaces"]}
    cls = {c["space_global_id"]: c for c in classification["spaces"]}
    storeys = {s["global_id"]: s for s in graph["storeys"]}
    geom = {r["space_global_id"]: r for r in (space_geom or {}).get("spaces", [])
            if r["geometry_status"] != "unavailable"}
    have_geom = bool(geom)

    # --- 1. name-prefix groups restricted to private-candidate scope -------
    groups: dict[str, list[str]] = defaultdict(list)
    shared, unassigned = [], []
    for gid, c in cls.items():
        if c["group_scope"] == "private_candidate" and c["prefix_group"]:
            groups[c["prefix_group"]].append(gid)
        elif c["classification"] == "private_apartment_space":
            unassigned.append(gid)
        else:
            shared.append(gid)

    # --- 2. duplicate / gap analysis --------------------------------------
    names_by_group = {g: [parse_space_name(spaces[i]["name"], pat) for i in ids] for g, ids in groups.items()}
    seq_type: dict[int, Counter] = defaultdict(Counter)           # seq -> modal room type across groups
    for g, ids in groups.items():
        for i in ids:
            p = parse_space_name(spaces[i]["name"], pat)
            seq_type[p["seq"]][(spaces[i]["long_name"] or "").lower()] += 1
    gap_seqs: dict[str, list[int]] = {}
    for g, plist in names_by_group.items():
        seqs = {p["seq"] for p in plist}
        gap_seqs[g] = [s for s in range(min(seqs), max(seqs) + 1) if s not in seqs]

    reassign: dict[str, dict] = {}
    dup_flags: dict[str, str] = {}
    for g, ids in groups.items():
        cnt = Counter(spaces[i]["name"] for i in ids)
        for i in ids:
            if cnt[spaces[i]["name"]] > 1:
                dup_flags[i] = "duplicate_space_name_in_group"
    for i in dup_flags:                                              # geometry-based resolution
        g = parse_space_name(spaces[i]["name"], pat)["group_key"]
        if not have_geom or i not in geom:
            continue
        sst = spaces[i]["storey_id"]
        own = [o for o in groups[g] if o != i and o not in dup_flags]
        d_own = _group_dist(i, own, geom)
        best_g, best_d = g, d_own if d_own is not None else 1e9
        for g2, ids2 in groups.items():
            if g2 == g:
                continue
            cand = [o for o in ids2 if spaces[o]["storey_id"] == sst and o not in dup_flags]
            d = _group_dist(i, cand, geom)
            if d is not None and d < best_d - 1e-6:
                best_g, best_d = g2, d
        if best_g != g and best_d <= tol and (d_own is None or d_own > tol):
            reassign[i] = {"from": g, "to": best_g, "distance_to_new_m": round(best_d, 3),
                           "distance_to_name_group_m": None if d_own is None else round(d_own, 3)}
    for i, r in reassign.items():
        groups[r["from"]].remove(i)
        groups[r["to"]].append(i)
    for g, ids in groups.items():                       # duplicates still unresolved after geometry
        cnt = Counter(spaces[i]["name"] for i in ids)
        for i in ids:
            if i in dup_flags and cnt[spaces[i]["name"]] <= 1 and i not in reassign:
                del dup_flags[i]

    # --- 3. zone / pset corroboration -------------------------------------
    zone_by_space = {sid: z["global_id"] for z in graph.get("zones", []) for sid in z["space_ids"]}
    keys = rules.get("pset_group_keys", [])

    def pset_value(sid: str):
        for ps in spaces[sid]["psets"].values():
            for k, v in ps.items():
                if any(x in k.lower() for x in keys) and v not in (None, ""):
                    return str(v)
        return None

    declared = _declared_count(graph, rules)
    candidates = []
    for g in sorted(groups, key=lambda k: (parse_space_name(spaces[groups[k][0]]["name"], pat)["prefix"],
                                           parse_space_name(spaces[groups[k][0]]["name"], pat)["number"])):
        ids = sorted(groups[g], key=lambda i: spaces[i]["name"])
        st_ids = sorted({spaces[i]["storey_id"] for i in ids if spaces[i]["storey_id"]},
                        key=lambda s: storeys[s]["elevation_m"] or 0.0)
        warnings: list[str] = []
        evidence: list[dict[str, Any]] = [
            {"signal": "name_prefix_group", "detail": f"{len(ids)} IfcSpaces share group token '{g}'"},
            {"signal": "dwelling_composition",
             "detail": classification["group_scopes"].get(g, {}).get("dwelling_signature_types")},
            {"signal": "storey_membership", "detail": [storeys[s]["name"] for s in st_ids]},
        ]
        score, basis = 0.55, ["name prefix group (+0.55)"]
        if len(st_ids) == 1:
            score += 0.15
            basis.append("all rooms on one storey (+0.15)")
        elif len(st_ids) > 1:
            warnings.append("unit spans multiple storeys; vertical continuity must be confirmed")
        # zones
        zs = {zone_by_space.get(i) for i in ids}
        if graph.get("zones"):
            if len(zs) == 1 and None not in zs:
                score += 0.1
                evidence.append({"signal": "ifc_zone", "detail": "all rooms belong to one IfcZone: agrees with name group"})
                basis.append("IfcZone agrees (+0.10)")
            else:
                warnings.append("IfcZone membership does not agree with name grouping")
        pv = {pset_value(i) for i in ids}
        if pv != {None}:
            evidence.append({"signal": "property_set", "detail": sorted(v for v in pv if v)})
            if len(pv - {None}) == 1:
                score += 0.05
                basis.append("property-set key agrees (+0.05)")
            else:
                warnings.append("property-set group keys disagree within the group")
        # geometry
        conn = "not_evaluated"
        if have_geom:
            with_g = [i for i in ids if i in geom]
            if len(with_g) < len(ids):
                warnings.append(f"{len(ids) - len(with_g)} rooms lack geometry; connectivity evaluated on the rest")
            if len(with_g) > 1:
                comps = _components(with_g, geom, tol)
                conn = "connected" if len(comps) == 1 else f"{len(comps)}_components"
                if len(comps) == 1:
                    score += 0.15
                    basis.append("rooms form one adjacency component (+0.15)")
                else:
                    warnings.append(f"rooms form {len(comps)} disconnected components at tol {tol} m")
                    evidence.append({"signal": "geometry_connectivity", "detail": [[spaces[x]["name"] for x in c] for c in comps]})
        else:
            warnings.append("no space geometry available: grouping is name/structure-based only")
            score = min(score, gr["max_confidence_without_geometry"])
        # duplicates / reassignment
        dups = [i for i in ids if i in dup_flags and i not in reassign]
        hinted: set[str] = set()
        for i in dups:
            warnings.append(f"ambiguous membership: space name '{spaces[i]['name']}' ({i}) occurs more than once")
            score -= 0.1
            hint = _gap_hint(i, g, spaces, pat, gap_seqs, groups, seq_type)
            if hint and spaces[i]["name"] not in hinted:
                hinted.add(spaces[i]["name"])
                evidence.append({"signal": "sequence_gap_hint", "detail": hint})
        for i, r in reassign.items():
            if i in ids and r["to"] == g:
                warnings.append(f"space '{spaces[i]['name']}' ({i}) carries the name-group '{r['from']}' but was assigned here by "
                                f"geometry (resolved; verify against source drawings)")
                evidence.append({"signal": "geometry_reassignment",
                                 "detail": f"{spaces[i]['name']} ({i}) moved from name-group {r['from']} to {g}; "
                                           f"adjacent at {r['distance_to_new_m']} m, {r['distance_to_name_group_m']} m from its name-group"})
                score += 0.05
        for i, r in reassign.items():
            if i not in ids and r["from"] == g:
                evidence.append({"signal": "geometry_reassignment_out", "detail": f"{spaces[i]['name']} moved to {r['to']}"})
        candidates.append({
            "candidate_id": _unit_id(g), "label": f"inferred dwelling group '{g}'", "group_key": g,
            "status": "inferred", "classification": UNIT_CLASSIFICATION,
            "legal_status": "not_a_legal_cadastral_unit", "ownership_status": "unknown_not_provided",
            "source_space_ids": ids, "source_space_names": [spaces[i]["name"] for i in ids],
            "source_storey_ids": st_ids, "storey_names": [storeys[s]["name"] for s in st_ids],
            "spaces": [{"global_id": i, "name": spaces[i]["name"], "long_name": spaces[i]["long_name"],
                        "function": cls[i]["function"], "flag": dup_flags.get(i)} for i in ids],
            "grouping_method": "name_prefix_composition" + ("+geometry" if have_geom else ""),
            "method_type": "rule_based", "model_status": "not_trained",
            "geometry_references": [{"space_global_id": i, "geometry_status": geom[i]["geometry_status"] if i in geom else "unavailable",
                                     "method": geom[i].get("method") if i in geom else None} for i in ids],
            "room_connectivity": conn, "grouping_evidence": evidence,
            "confidence": round(max(0.05, min(score, 0.95)), 2), "confidence_basis": basis,
            "derivation_method": ["IfcSpace prefix-group composition", "storey membership",
                                  "adjacency/duplicate resolution when geometry exists"],
            "warnings": warnings,
        })

    unit_count = len(candidates)
    return {
        "method": "rule_based", "method_type": "name_prefix_composition+geometry" if have_geom else "name_prefix_composition",
        "model_status": "not_trained", "source_mode": graph["source_mode"],
        "label_policy": "derived/inferred prototype property units; NOT official apartments or legal cadastral units",
        "declared_count_check": _compare_declared(declared, unit_count),
        "summary": {"ifc_space_count": len(spaces), "inferred_property_unit_count": unit_count,
                    "spaces_in_units": sum(len(c["source_space_ids"]) for c in candidates),
                    "common_or_service_spaces": len(shared), "unassigned_private_like_spaces": len(unassigned),
                    "geometry_used": have_geom, "reassigned_by_geometry": len(reassign),
                    "ambiguous_space_names": sorted({spaces[i]["name"] for i in dup_flags})},
        "candidates": candidates,
        "common_service_spaces": [{"global_id": i, "name": spaces[i]["name"], "long_name": spaces[i]["long_name"],
                                   "classification": cls[i]["classification"], "storey": cls[i]["storey_name"]} for i in shared],
        "unassigned_spaces": [{"global_id": i, "name": spaces[i]["name"]} for i in unassigned],
    }


def _gap_hint(i, g, spaces, pat, gap_seqs, groups, seq_type):
    me = spaces[i]
    typ = (me["long_name"] or "").lower()
    out = []
    for g2, gaps in gap_seqs.items():
        if g2 == g:
            continue
        for s in gaps:
            modal = seq_type[s].most_common(1)[0][0] if seq_type.get(s) else None
            if modal == typ:
                out.append(f"group '{g2}' has no sequence {s:02d}; other groups use sequence {s:02d} for '{modal}', "
                           f"so one '{me['name']}' may belong to group '{g2}' (hint only; resolved by geometry when available)")
    return out or None


def _declared_count(graph: dict, rules: dict) -> int | None:
    m = re.search(rules["declared_count"]["pattern"], (graph["project"].get("name") or ""), re.I)
    return int(m.group("n")) if m else None


def _compare_declared(declared: int | None, derived: int) -> dict[str, Any]:
    if declared is None:
        return {"declared_in_ifc_project_name": None, "derived": derived, "agrees": None,
                "note": "no unit count declared in IFC project name"}
    return {"declared_in_ifc_project_name": declared, "derived": derived, "agrees": declared == derived,
            "note": "cross-check only; the derived count is not forced to the declared count"}
