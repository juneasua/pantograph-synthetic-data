"""
fit_box.py

Rebuilds box-like CAD parts (plates, rails, blocks) as oriented cubes. Face
normals are grouped by direction and weighted by area: the biggest flat side
gives the first axis, the biggest side perpendicular to it the second. The
part is then measured along those axes and a matching cube is built,
named "box_<name>".

Usage:
    Select one or more reference parts (in the Outliner) and run.

Functions:
    mesh_data(node)               -- world points and triangle vertex indices
    box_axes(points, tri_verts)   -- the box's three axes
    fit_box(node)                 -- builds the fitted cube
    main()                        -- runs on the selection

Author:
    June

Changelog:
    2026-10-14  Cleaned up for portfolio release.

Environment:
    Autodesk Maya 2024, Python 3.10, maya.cmds, maya.api.OpenMaya
"""
import maya.cmds as cmds
import maya.api.OpenMaya as om

ALIGN_TOLERANCE = 0.995  # how parallel two faces must be to count as the same side (~6 degrees)


def mesh_data(node):
    sel = om.MSelectionList()
    sel.add(node)
    dag = sel.getDagPath(0)
    dag.extendToShape()
    fn = om.MFnMesh(dag)
    pts = [om.MVector(p) for p in fn.getPoints(om.MSpace.kWorld)]
    _, tri_verts = fn.getTriangles()
    return pts, tri_verts


def box_axes(pts, tri_verts):
    """Find the box's 3 axes from its biggest flat sides."""
    clusters = []  # [direction, total area]
    for i in range(0, len(tri_verts), 3):
        a, b, c = (pts[tri_verts[i + k]] for k in range(3))
        cross = (b - a) ^ (c - a)
        area = cross.length() * 0.5
        if area < 1e-9:
            continue
        n = cross.normal()
        for cl in clusters:
            d = cl[0] * n
            if abs(d) > ALIGN_TOLERANCE:
                if d < 0:          # opposite sides of a box count as one direction
                    n = -n
                cl[0] = (cl[0] * cl[1] + n * area).normal()
                cl[1] += area
                break
        else:
            clusters.append([n, area])
    clusters.sort(key=lambda cl: cl[1], reverse=True)

    x = clusters[0][0]
    y = None
    for cl in clusters[1:]:
        if abs(cl[0] * x) < 0.1:   # roughly perpendicular to the biggest side
            y = cl[0]
            break
    if y is None:                  # no second flat side found: pick any perpendicular
        y = om.MVector(0, 1, 0) if abs(x.y) < 0.9 else om.MVector(1, 0, 0)
    y = (y - x * (y * x)).normal()
    z = x ^ y
    return x, y, z


def fit_box(node):
    pts, tri_verts = mesh_data(node)
    axes = box_axes(pts, tri_verts)

    size, mid = [], om.MVector()
    for axis in axes:
        proj = [p * axis for p in pts]
        lo, hi = min(proj), max(proj)
        size.append(hi - lo)
        mid += axis * ((lo + hi) / 2.0)

    name = node.replace("cad_", "box_", 1)
    box = cmds.polyCube(name=name, width=size[0], height=size[1], depth=size[2])[0]
    x, y, z = axes
    cmds.xform(box, worldSpace=True, matrix=[x.x, x.y, x.z, 0,
                                             y.x, y.y, y.z, 0,
                                             z.x, z.y, z.z, 0,
                                             mid.x, mid.y, mid.z, 1])
    cmds.delete(box, constructionHistory=True)
    print("%s: %.2f x %.2f x %.2f cm" % (box, size[0], size[1], size[2]))
    return box


def main():
    for node in cmds.ls(sl=True, type="transform"):
        fit_box(node)


if __name__ == "__main__":
    main()
