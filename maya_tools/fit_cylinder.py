"""
fit_cylinder.py

Rebuilds tube-like CAD parts as clean cylinders. For each selected mesh it
finds the tube's main axis from its points (principal component analysis),
measures the length and the radius at each end, and builds a matching,
correctly oriented and tapered polyCylinder named "fit_<name>".

Usage:
    Select one or more reference tubes (in the Outliner) and run.

Functions:
    world_points(node)   -- world-space vertex positions of a mesh
    main_axis(points, c) -- direction of largest spread (power iteration)
    fit_cylinder(node)   -- builds the fitted cylinder
    main()               -- runs on the selection

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

SIDES = 12      # sides around the tube
END_ZONE = 0.1  # fraction of the length used to measure each end's radius


def world_points(node):
    sel = om.MSelectionList()
    sel.add(node)
    dag = sel.getDagPath(0)
    dag.extendToShape()
    return [om.MVector(p) for p in om.MFnMesh(dag).getPoints(om.MSpace.kWorld)]


def main_axis(points, center):
    """Direction in which the points spread the most (the tube's axis)."""
    cov = [[0.0] * 3 for _ in range(3)]
    for p in points:
        d = p - center
        v = (d.x, d.y, d.z)
        for i in range(3):
            for j in range(3):
                cov[i][j] += v[i] * v[j]
    axis = om.MVector(1.0, 0.7, 0.3).normal()
    for _ in range(50):
        axis = om.MVector(*[sum(cov[i][k] * axis[k] for k in range(3)) for i in range(3)]).normal()
    return axis


def fit_cylinder(node, sides=SIDES):
    pts = world_points(node)
    center = om.MVector()
    for p in pts:
        center += p
    center /= len(pts)
    axis = main_axis(pts, center)

    ts = [(p - center) * axis for p in pts]  # position of each point along the axis
    t_min, t_max = min(ts), max(ts)
    length = t_max - t_min
    zone = length * END_ZONE

    def radius_near(t_end):
        return max(((p - center) - axis * t).length()
                   for p, t in zip(pts, ts) if abs(t - t_end) <= zone)

    r_bottom, r_top = radius_near(t_min), radius_near(t_max)

    name = node.replace("cad_", "fit_", 1)
    cyl = cmds.polyCylinder(name=name, radius=r_bottom, height=length,
                            subdivisionsX=sides, subdivisionsY=1,
                            subdivisionsCaps=1, axis=(0, 1, 0))[0]

    # Taper: scale the top ring to the top radius
    top = [v for v in cmds.ls(cyl + ".vtx[*]", flatten=True)
           if cmds.pointPosition(v, local=True)[1] > 0]
    s = r_top / r_bottom
    cmds.scale(s, 1, s, top, pivot=(0, length / 2.0, 0), relative=True)

    # Align the cylinder's Y axis with the tube's axis and move it into place
    rot = om.MQuaternion(om.MVector(0, 1, 0), axis).asEulerRotation()
    mid = center + axis * ((t_min + t_max) / 2.0)
    cmds.xform(cyl, worldSpace=True,
               rotation=[math.degrees(a) for a in (rot.x, rot.y, rot.z)],
               translation=[mid.x, mid.y, mid.z])
    cmds.delete(cyl, constructionHistory=True)
    print("%s: length %.2f cm, radius %.2f -> %.2f cm" % (cyl, length, r_bottom, r_top))
    return cyl


def main():
    for node in cmds.ls(sl=True, type="transform"):
        fit_cylinder(node)


if __name__ == "__main__":
    main()
