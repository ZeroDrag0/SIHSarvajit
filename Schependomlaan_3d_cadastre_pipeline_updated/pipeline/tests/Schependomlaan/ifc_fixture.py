"""Synthetic IFC2X3 fixture used ONLY by tests. It mirrors the *structure* observed in the real
Schependomlaan file (spaces aggregated under storeys, no ContainedInStructure, mm units, a duplicated
space name) but is NOT Schependomlaan data."""
from __future__ import annotations

import ifcopenshell
import ifcopenshell.guid as guid


def build(path: str) -> str:
    f = ifcopenshell.file(schema="IFC2X3")
    g = guid.new
    pt = lambda *c: f.createIfcCartesianPoint(list(map(float, c)))
    ax3 = lambda x=0, y=0, z=0: f.createIfcAxis2Placement3D(pt(x, y, z), None, None)
    lp = lambda rel, x=0, y=0, z=0: f.createIfcLocalPlacement(rel, ax3(x, y, z))

    ua = f.createIfcUnitAssignment([
        f.createIfcSIUnit(None, "LENGTHUNIT", "MILLI", "METRE"),
        f.createIfcSIUnit(None, "AREAUNIT", None, "SQUARE_METRE"),
        f.createIfcSIUnit(None, "VOLUMEUNIT", None, "CUBIC_METRE")])
    ctx = f.createIfcGeometricRepresentationContext(None, "Model", 3, 1e-5, ax3(), None)
    sub = {n: f.createIfcGeometricRepresentationSubContext(n, "Model", None, None, None, None, ctx, None, "MODEL_VIEW", None)
           for n in ("Body", "FootPrint", "Box")}
    project = f.createIfcProject(g(), None, "3 Appartementen Fixture", None, None, None, None, [ctx], ua)
    site_pl = lp(None)
    site = f.createIfcSite(g(), None, "Site", None, None, site_pl, None, None, "ELEMENT")
    bld_pl = lp(site_pl)
    bld = f.createIfcBuilding(g(), None, "Building", None, None, bld_pl, None, None, "ELEMENT")
    f.createIfcRelAggregates(g(), None, None, None, project, [site])
    f.createIfcRelAggregates(g(), None, None, None, site, [bld])

    storeys = {}
    for name, z in (("00 begane grond", 0), ("01 eerste verdieping", 3000), ("04 dak", 6000)):
        pl = lp(bld_pl, 0, 0, z)
        storeys[name] = (f.createIfcBuildingStorey(g(), None, name, None, None, pl, None, None, "ELEMENT", float(z)), pl)
    f.createIfcRelAggregates(g(), None, None, None, bld, [s for s, _ in storeys.values()])

    def body(w, d, h):
        prof = f.createIfcRectangleProfileDef("AREA", None, f.createIfcAxis2Placement2D(f.createIfcCartesianPoint([w / 2, d / 2]), None), w, d)
        solid = f.createIfcExtrudedAreaSolid(prof, ax3(), f.createIfcDirection([0., 0., 1.]), h)
        return f.createIfcProductDefinitionShape(None, None, [f.createIfcShapeRepresentation(sub["Body"], "Body", "SweptSolid", [solid])])

    def fallback(w, d, h):
        poly = f.createIfcPolyline([pt(0, 0), pt(w, 0), pt(w, d), pt(0, d), pt(0, 0)])
        fp = f.createIfcShapeRepresentation(sub["FootPrint"], "FootPrint", "GeometricCurveSet", [f.createIfcGeometricCurveSet([poly])])
        box = f.createIfcShapeRepresentation(sub["Box"], "Box", "BoundingBox", [f.createIfcBoundingBox(pt(0, 0, 0), w, d, h)])
        return f.createIfcProductDefinitionShape(None, None, [fp, box])

    W, D, H, GAP = 4000, 3000, 2600, 100
    # (name, long_name, storey, x_m*1000, y_m*1000, representation)
    spec = [
        ("1.00", "entree", "00 begane grond", 0, 0, "body"),
        ("1.02", "toilet", "00 begane grond", W + GAP, 0, "body"),
        ("1.03", "woonkamer", "00 begane grond", 0, D + GAP, "body"),
        ("1.04", "keuken", "00 begane grond", W + GAP, D + GAP, "body"),
        ("2.00", "entree", "00 begane grond", 10000, 0, "fallback"),
        ("2.03", "woonkamer", "00 begane grond", 10000, D + GAP, "fallback"),
        ("2.04", "keuken", "00 begane grond", 10000 + W + GAP, D + GAP, "fallback"),
        ("1.02", "toilet", "00 begane grond", 10000 + W + GAP, 0, "body"),     # stray duplicate belongs physically to apt 2
        ("A0.00", "entree", "00 begane grond", 20000, 0, "body"),
        ("A0.02", "berging", "00 begane grond", 20000, D + GAP, "none"),
        ("3.00", "entree", "01 eerste verdieping", 0, 0, "body"),
        ("3.03", "woonkamer", "01 eerste verdieping", 0, D + GAP, "body"),
        ("3.04", "keuken", "01 eerste verdieping", W + GAP, D + GAP, "body"),
        ("A1.01", "overloop", "01 eerste verdieping", 20000, 0, "body"),
    ]
    by_storey: dict[str, list] = {}
    for name, long_name, st, x, y, rep in spec:
        s, spl = storeys[st]
        shape = {"body": body, "fallback": fallback}.get(rep)
        sp = f.createIfcSpace(g(), None, name, None, None, lp(spl, x, y, 0), shape(W, D, H) if shape else None, long_name,
                              "ELEMENT", "INTERNAL", None)
        by_storey.setdefault(st, []).append(sp)
    for st, sps in by_storey.items():                         # aggregates ONLY, deliberately no containment relation
        f.createIfcRelAggregates(g(), None, None, None, storeys[st][0], sps)
    f.write(path)
    return path
