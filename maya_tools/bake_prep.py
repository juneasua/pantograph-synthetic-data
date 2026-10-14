"""
bake_prep.py

Prepares the scene for a name-matched bake in Marmoset Toolbag. Every CAD
part ("cad_*") is assigned to the low-poly mesh ("*_geo") whose surface it is
closest to, measured as the average distance from sample points on the CAD
part to the low-poly surface. The script then builds two groups for export:
bake_low_grp with "<part>_low" copies and bake_high_grp with "<part>_high"
meshes (all CAD parts assigned to that low-poly, merged).

Usage:
    Run with the low-poly parts and the CAD reference in the scene, then
    export bake_low_grp and bake_high_grp as FBX for Toolbag.

Functions:
    assign()            -- {low: [cad parts]}
    build_groups(a)     -- creates the _low / _high copies
    main()

Author:
    June

Changelog:
    2026-10-14  Cleaned up for portfolio release.

Environment:
    Autodesk Maya 2024, Python 3.10, maya.cmds, maya.api.OpenMaya
"""
import maya.cmds as cmds
import maya.api.OpenMaya as om

LOW_PATTERN = "*_geo"
HIGH_PATTERN = "cad_*"
CANDIDATES = 5   # only the 5 nearest low-poly parts (by bounding box) are measured
SAMPLES = 150    # sample points per CAD part


def is_mesh(node):
    return bool(cmds.listRelatives(node, shapes=True, type="mesh"))


def mesh_fn(node):
    sel = om.MSelectionList()
    sel.add(node)
    dag = sel.getDagPath(0)
    dag.extendToShape()
    return om.MFnMesh(dag)


def bbox_gap(a, b):
    """Distance between two world bounding boxes (0 if they overlap)."""
    d2 = 0.0
    for i in range(3):
        gap = max(a[i] - b[i + 3], b[i] - a[i + 3], 0.0)
        d2 += gap * gap
    return d2 ** 0.5


def sample_points(fn):
    pts = fn.getPoints(om.MSpace.kWorld)
    step = max(1, len(pts) // SAMPLES)
    return [pts[i] for i in range(0, len(pts), step)]


def mean_distance(points, fn):
    total = 0.0
    for p in points:
        q = fn.getClosestPoint(p, om.MSpace.kWorld)[0]
        total += (q - p).length()
    return total / len(points)


def assign():
    lows = [n for n in cmds.ls(LOW_PATTERN, type="transform") if is_mesh(n)]
    highs = [n for n in cmds.ls(HIGH_PATTERN, type="transform") if is_mesh(n)]
    low_bb = {n: cmds.exactWorldBoundingBox(n) for n in lows}
    low_fn = {n: mesh_fn(n) for n in lows}
    result = {n: [] for n in lows}
    for high in highs:
        hb = cmds.exactWorldBoundingBox(high)
        near = sorted(lows, key=lambda n: bbox_gap(hb, low_bb[n]))[:CANDIDATES]
        pts = sample_points(mesh_fn(high))
        best = min(near, key=lambda n: mean_distance(pts, low_fn[n]))
        result[best].append(high)
    return result


def build_groups(assignments):
    for grp in ("bake_low_grp", "bake_high_grp"):
        if cmds.objExists(grp):
            cmds.delete(grp)
    low_grp = cmds.group(empty=True, name="bake_low_grp")
    high_grp = cmds.group(empty=True, name="bake_high_grp")
    for low, highs in sorted(assignments.items()):
        if not highs:
            print("WARNING: no CAD parts assigned to %s" % low)
            continue
        base = low[:-4] if low.endswith("_geo") else low
        low_copy = cmds.duplicate(low, name=base + "_low")[0]
        cmds.parent(low_copy, low_grp)
        copies = [cmds.duplicate(h)[0] for h in highs]
        if len(copies) == 1:
            high = cmds.rename(copies[0], base + "_high")
        else:
            high = cmds.polyUnite(copies, name=base + "_high", ch=False)[0]
            for c in copies:
                if cmds.objExists(c):
                    cmds.delete(c)
        cmds.parent(high, high_grp)
        print("%-35s <- %d CAD parts" % (base, len(highs)))


def main():
    build_groups(assign())


if __name__ == "__main__":
    main()
