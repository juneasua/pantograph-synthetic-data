"""
simplify_outline.py

Rebuilds flat CAD plates as clean low-poly plates. It finds the plate's
largest flat side, walks its outer border, and keeps only the points that
matter: sharp corners, the tangent points where a curve meets a straight
edge, and one point every few degrees along curves. The simplified outline
is extruded to the plate's measured thickness, named "plate_<name>".

Usage:
    Select one or more CAD plates and run.

Functions:
    plate_normal(fn)            -- direction of the largest flat side
    outer_loop(fn, faces)       -- ordered outer border vertices
    simplify(points)            -- keeps corners, tangent points, arc steps
    rebuild_plate(node)         -- builds the extruded low-poly plate
    main()                      -- runs on the selection

Author:
    June

Changelog:
    2026-10-14  Cleaned up for portfolio release.

Environment:
    Autodesk Maya 2024, Python 3.10, maya.cmds, maya.api.OpenMaya
"""
import math

import maya.cmds as cmds
import maya.api.OpenMaya as om

CORNER_DEG = 25.0      # a turn sharper than this is a corner: always kept
ARC_STEP_DEG = 30.0    # along curves, keep a point every 30 degrees of turning
STRAIGHT_DEG = 2.0     # turns below this count as straight (for tangent points)
FACE_TOLERANCE = 0.995 # how parallel a face must be to belong to the flat side
HEIGHT_TOLERANCE = 0.01


def mesh_fn(node):
    sel = om.MSelectionList()
    sel.add(node)
    dag = sel.getDagPath(0)
    dag.extendToShape()
    return om.MFnMesh(dag)


def plate_normal(fn):
    """Area-weighted direction of the biggest flat side."""
    clusters = []
    for f in range(fn.numPolygons):
        n = fn.getPolygonNormal(f, om.MSpace.kWorld)
        area = fn.getPolygonArea(f, om.MSpace.kWorld)
        for cl in clusters:
            if cl[0] * n > FACE_TOLERANCE:
                cl[1] += area
                break
        else:
            clusters.append([om.MVector(n), area])
    return max(clusters, key=lambda cl: cl[1])[0].normal()


def flat_side_faces(fn, n, pts):
    faces, heights = [], {}
    for f in range(fn.numPolygons):
        if fn.getPolygonNormal(f, om.MSpace.kWorld) * n > FACE_TOLERANCE:
            heights[f] = om.MVector(pts[fn.getPolygonVertices(f)[0]]) * n
    top = max(heights.values())
    return [f for f, h in heights.items() if top - h < HEIGHT_TOLERANCE]


def outer_loop(fn, faces, pts):
    """Ordered vertex indices of the longest border loop of the face set."""
    count = {}
    for f in faces:
        vs = list(fn.getPolygonVertices(f))
        for a, b in zip(vs, vs[1:] + vs[:1]):
            key = (min(a, b), max(a, b))
            count[key] = count.get(key, 0) + 1
    adj = {}
    for (a, b), c in count.items():
        if c == 1:
            adj.setdefault(a, []).append(b)
            adj.setdefault(b, []).append(a)

    loops, seen = [], set()
    for start in adj:
        if start in seen:
            continue
        loop, prev, cur = [start], None, start
        seen.add(start)
        while True:
            nxt = [v for v in adj[cur] if v != prev and v not in seen]
            if not nxt:
                break
            prev, cur = cur, nxt[0]
            loop.append(cur)
            seen.add(cur)
        loops.append(loop)

    def perimeter(loop):
        return sum((om.MVector(pts[loop[i]]) - om.MVector(pts[loop[i - 1]])).length()
                   for i in range(len(loop)))
    return max(loops, key=perimeter)


def simplify(points):
    pts = [p for i, p in enumerate(points) if (p - points[i - 1]).length() > 1e-6]
    n = len(pts)

    def turn(i):
        a = (pts[i] - pts[i - 1]).normal()
        b = (pts[(i + 1) % n] - pts[i]).normal()
        return math.degrees(math.acos(max(-1.0, min(1.0, a * b))))

    turns = [turn(i) for i in range(n)]
    keep, acc = [], 0.0
    for i in range(n):
        acc += turns[i]
        tangent = (turns[i] < STRAIGHT_DEG) != (turns[i - 1] < STRAIGHT_DEG)
        if turns[i] >= CORNER_DEG or acc >= ARC_STEP_DEG or tangent:
            keep.append(pts[i])
            acc = 0.0
    return keep if len(keep) >= 3 else pts


def rebuild_plate(node):
    fn = mesh_fn(node)
    pts = fn.getPoints(om.MSpace.kWorld)
    n = plate_normal(fn)
    heights = [om.MVector(p) * n for p in pts]
    bottom, thickness = min(heights), max(heights) - min(heights)

    loop = outer_loop(fn, flat_side_faces(fn, n, pts), pts)
    flat = []
    for i in loop:
        p = om.MVector(pts[i])
        flat.append(p - n * (p * n - bottom))  # project onto the bottom plane
    outline = simplify(flat)

    name = node.replace("cad_", "plate_", 1)
    plate = cmds.polyCreateFacet(p=[(v.x, v.y, v.z) for v in outline], name=name)[0]
    if mesh_fn(plate).getPolygonNormal(0, om.MSpace.kWorld) * n < 0:
        cmds.polyNormal(plate, normalMode=0, userNormalMode=0, ch=False)
    cmds.polyExtrudeFacet(plate + ".f[0]", localTranslateZ=thickness, keepFacesTogether=True)
    cmds.polyCloseBorder(plate)
    cmds.delete(plate, constructionHistory=True)
    print("%s: outline %d -> %d points, thickness %.2f cm"
          % (plate, len(loop), len(outline), thickness))
    return plate


def main():
    for node in cmds.ls(sl=True, type="transform"):
        rebuild_plate(node)


if __name__ == "__main__":
    main()
