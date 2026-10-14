"""
control_shapes.py

Replaces the curve shape of one or more controls with a custom curve, while
keeping each control's transform, connections, attributes and colour. Used to
give the clamp controls a shape that reads clearly in the viewport.

Usage:
    Model the custom curve at the origin, at the size you want it on the
    control. Select the custom curve first, then the controls, and run.

Functions:
    swap_shape(source, ctrl)  -- replaces ctrl's shapes with a copy of source's
    main()

Author:
    June

Changelog:
    2026-10-14  Cleaned up for portfolio release.

Environment:
    Autodesk Maya 2024, Python 3.10, maya.cmds
"""
import maya.cmds as cmds


def swap_shape(source, ctrl):
    old = cmds.listRelatives(ctrl, shapes=True, type="nurbsCurve") or []
    color = None
    if old and cmds.getAttr(old[0] + ".overrideEnabled"):
        color = cmds.getAttr(old[0] + ".overrideColor")
    if old:
        cmds.delete(old)

    temp = cmds.duplicate(source)[0]
    shapes = cmds.listRelatives(temp, shapes=True, type="nurbsCurve") or []
    for i, shape in enumerate(shapes):
        new = cmds.parent(shape, ctrl, relative=True, shape=True)[0]
        new = cmds.rename(new, "%sShape%s" % (ctrl, i + 1 if i else ""))
        if color is not None:
            cmds.setAttr(new + ".overrideEnabled", 1)
            cmds.setAttr(new + ".overrideColor", color)
    cmds.delete(temp)


def main():
    sel = cmds.ls(sl=True, type="transform")
    if len(sel) < 2:
        cmds.error("Select the custom curve first, then the controls.")
    for ctrl in sel[1:]:
        swap_shape(sel[0], ctrl)
    print("Swapped the shape on %d controls." % (len(sel) - 1))


if __name__ == "__main__":
    main()
