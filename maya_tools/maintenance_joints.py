"""
maintenance_joints.py

Adds the maintenance part of the rig: one joint and one control for every
contact strip and strip clamp, so a strip can be unclamped, lifted out and
replaced. Joints go under head_jnt at each part's centre; controls go under
head_ctrl so they ride along when the pantograph raises. Strip controls get
a "wear" attribute (0 = new, 1 = fully worn) used by wear_blendshapes.py.

Colours follow the side: L blue, R red, C yellow.

Usage:
    Run after rig_builder.py. Parts must be named
    "<side>_contactStrip_<nn>_geo" and "<side>_stripClamp_<nn>_geo".

Functions:
    add_part(mesh, wear)        -- joint + control for one part
    main()

Author:
    June

Changelog:
    2026-10-14  Cleaned up for portfolio release.

Environment:
    Autodesk Maya 2024, Python 3.10, maya.cmds
"""
import maya.cmds as cmds

HEAD_JNT = "head_jnt"
HEAD_CTRL = "head_ctrl"
COLORS = {"L": 6, "R": 13, "C": 17}
PADDING = 1.2  # control size relative to the part


def box_curve(name, sx, sy, sz):
    x, y, z = sx / 2.0, sy / 2.0, sz / 2.0
    pts = [(-x, y, z), (x, y, z), (x, y, -z), (-x, y, -z), (-x, y, z), (-x, -y, z),
           (x, -y, z), (x, y, z), (x, -y, z), (x, -y, -z), (x, y, -z), (x, -y, -z),
           (-x, -y, -z), (-x, y, -z), (-x, -y, -z), (-x, -y, z)]
    return cmds.curve(name=name, degree=1, point=pts)


def add_part(mesh, wear):
    base = mesh[:-4]  # drop "_geo"
    side = base.split("_")[0]
    bb = cmds.exactWorldBoundingBox(mesh)
    pos = ((bb[0] + bb[3]) / 2.0, (bb[1] + bb[4]) / 2.0, (bb[2] + bb[5]) / 2.0)
    size = [(bb[i + 3] - bb[i]) * PADDING for i in range(3)]

    cmds.select(HEAD_JNT)
    jnt = cmds.joint(name=base + "_jnt", position=pos)

    grp = cmds.group(empty=True, name=base + "_ctrl_grp")
    cmds.xform(grp, ws=True, translation=pos)
    ctrl = box_curve(base + "_ctrl", *size)
    cmds.parent(ctrl, grp, relative=True)
    cmds.parent(grp, HEAD_CTRL)
    for shape in cmds.listRelatives(ctrl, shapes=True):
        cmds.setAttr(shape + ".overrideEnabled", 1)
        cmds.setAttr(shape + ".overrideColor", COLORS.get(side, 17))
    for attr in ("sx", "sy", "sz"):
        cmds.setAttr(ctrl + "." + attr, lock=True, keyable=False)
    if wear:
        cmds.addAttr(ctrl, longName="wear", attributeType="double", min=0, max=1,
                     defaultValue=0, keyable=True)
    cmds.parentConstraint(ctrl, jnt, maintainOffset=True)
    return jnt, ctrl


def main():
    strips = sorted(cmds.ls("*_contactStrip_*_geo", type="transform"))
    clamps = sorted(cmds.ls("*_stripClamp_*_geo", type="transform"))
    for mesh in strips:
        add_part(mesh, wear=True)
    for mesh in clamps:
        add_part(mesh, wear=False)
    print("Added %d strip and %d clamp controls." % (len(strips), len(clamps)))


if __name__ == "__main__":
    main()
