"""
place_copies.py

Places copies of a finished low-poly piece onto every other CAD copy of the
same part (left/right and front/back repeats). For each reference it moves a
duplicate onto the reference's centre, tries all 24 axis-aligned orientations
with a short ICP run, keeps the best one, and refines it with a full ICP run.
Copies are named "copy_<reference name>".

Usage:
    Put this folder on Maya's Python path (needs icp_align.py).
    Select the finished low-poly piece first, then the other CAD copies, and run.

Functions:
    centre(node)            -- world bounding box centre
    orientations()          -- the 24 rotations of a cube
    place(source, ref)      -- best-fit copy of source on ref
    main()                  -- runs on the selection

Author:
    June

Changelog:
    2026-10-14  Cleaned up for portfolio release.

Environment:
    Autodesk Maya 2024, Python 3.10, maya.cmds, maya.api.OpenMaya
"""
import itertools

import maya.cmds as cmds
import maya.api.OpenMaya as om

from icp_align import align

QUICK_STEPS = 8  # ICP steps used to score each orientation


def centre(node):
    bb = cmds.exactWorldBoundingBox(node)
    return om.MVector((bb[0] + bb[3]) / 2.0, (bb[1] + bb[4]) / 2.0, (bb[2] + bb[5]) / 2.0)


def translation(v):
    return om.MMatrix([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, v.x, v.y, v.z, 1])


def get_world(node):
    return om.MMatrix(cmds.xform(node, q=True, ws=True, matrix=True))


def set_world(node, m):
    cmds.xform(node, ws=True, matrix=[m.getElement(r, c) for r in range(4) for c in range(4)])


def orientations():
    """All 24 rotations that map the X/Y/Z axes onto each other."""
    mats = []
    for perm in itertools.permutations(range(3)):
        for signs in itertools.product((1.0, -1.0), repeat=3):
            flat = [0.0] * 16
            flat[15] = 1.0
            for row in range(3):
                flat[row * 4 + perm[row]] = signs[row]
            m = om.MMatrix(flat)
            if m.det3x3() > 0:  # rotations only, no mirroring
                mats.append(m)
    return mats


def place(source, ref):
    start = get_world(source)
    c_src, c_ref = centre(source), centre(ref)
    best = None
    for k, rot in enumerate(orientations()):
        cand = cmds.duplicate(source, name="%s_try%02d" % (source, k))[0]
        set_world(cand, start * translation(-c_src) * rot * translation(c_ref))
        gap = align(cand, [ref], iterations=QUICK_STEPS, verbose=False)
        if best is None or gap < best[0]:
            if best:
                cmds.delete(best[1])
            best = (gap, cand)
        else:
            cmds.delete(cand)
    gap = align(best[1], [ref], verbose=False)
    name = cmds.rename(best[1], "copy_" + ref.replace("cad_", "", 1))
    print("%s placed, average gap %.4f cm" % (name, gap))
    return name


def main():
    sel = cmds.ls(sl=True, type="transform")
    if len(sel) < 2:
        cmds.error("Select the finished low-poly piece first, then the other CAD copies.")
    cmds.undoInfo(openChunk=True)
    try:
        for ref in sel[1:]:
            place(sel[0], ref)
    finally:
        cmds.undoInfo(closeChunk=True)


if __name__ == "__main__":
    main()
