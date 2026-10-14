"""
rig_builder.py

Builds the pantograph's raising rig from the geometry itself. The hinge axis
is measured from each main shaft (its longest direction), the joints are
placed at the centres of the shaft, knee and apex parts, and each side gets a
2-bone IK chain whose pole vector lies in the plane perpendicular to the
hinge, so the arms can only fold the way the real hinges allow.

The script also computes the safe raise height: how far the head can go up
before either arm reaches REACH_CAP (90%) of its full length. A single
"raise" attribute (0 to 1) on main_ctrl drives the head up to that height.

Hierarchy:
    root_jnt
        L_lowerArm_jnt > L_upperArm_jnt > L_apex_jnt   (IK to head_ctrl)
        R_lowerArm_jnt > R_upperArm_jnt > R_apex_jnt   (IK to head_ctrl)
        head_jnt                                         (follows head_ctrl)

Usage:
    Edit HINGES to match your part names, then run in the rest
    (lowered) pose.

Functions:
    centre(node), main_axis(node)  -- measurements from the geometry
    safe_raise(sides)              -- maximum head lift in cm
    build()                        -- joints, IK, controls and the raise link

Author:
    June

Changelog:
    2026-10-14  Cleaned up for portfolio release.

Environment:
    Autodesk Maya 2024, Python 3.10, maya.cmds, maya.api.OpenMaya
"""
import maya.cmds as cmds
import maya.api.OpenMaya as om

HINGES = {
    "L": {"shaft": "L_mainShaft_geo", "knee": "L_knee_geo", "apex": "L_apexFitting_geo"},
    "R": {"shaft": "R_mainShaft_geo", "knee": "R_knee_geo", "apex": "R_apexFitting_geo"},
}
REACH_CAP = 0.9   # never stretch an arm past 90% of its length
POLE_DISTANCE = 50.0
COLORS = {"L": 6, "R": 13, "C": 17}  # blue, red, yellow


def centre(node):
    bb = cmds.exactWorldBoundingBox(node)
    return om.MVector((bb[0] + bb[3]) / 2.0, (bb[1] + bb[4]) / 2.0, (bb[2] + bb[5]) / 2.0)


def main_axis(node):
    """Longest direction of a part's points (a shaft's axis = the hinge axis)."""
    sel = om.MSelectionList()
    sel.add(node)
    dag = sel.getDagPath(0)
    dag.extendToShape()
    pts = [om.MVector(p) for p in om.MFnMesh(dag).getPoints(om.MSpace.kWorld)]
    c = sum(pts, om.MVector()) * (1.0 / len(pts))
    cov = [[0.0] * 3 for _ in range(3)]
    for p in pts:
        d = p - c
        v = (d.x, d.y, d.z)
        for i in range(3):
            for j in range(3):
                cov[i][j] += v[i] * v[j]
    axis = om.MVector(1.0, 0.7, 0.3).normal()
    for _ in range(50):
        axis = om.MVector(*[sum(cov[i][k] * axis[k] for k in range(3)) for i in range(3)]).normal()
    return axis


def tup(v):
    return (v.x, v.y, v.z)


def colour(node, side):
    for shape in cmds.listRelatives(node, shapes=True) or []:
        cmds.setAttr(shape + ".overrideEnabled", 1)
        cmds.setAttr(shape + ".overrideColor", COLORS[side])


def box_curve(name, size):
    s = size / 2.0
    pts = [(-s, s, s), (s, s, s), (s, s, -s), (-s, s, -s), (-s, s, s), (-s, -s, s),
           (s, -s, s), (s, s, s), (s, -s, s), (s, -s, -s), (s, s, -s), (s, -s, -s),
           (-s, -s, -s), (-s, s, -s), (-s, -s, -s), (-s, -s, s)]
    return cmds.curve(name=name, degree=1, point=pts)


def safe_raise(sides):
    """Largest straight-up head lift that keeps both arms within REACH_CAP."""
    lifts = []
    for s in sides.values():
        reach = REACH_CAP * ((s["knee"] - s["shaft"]).length() + (s["apex"] - s["knee"]).length())
        d = s["apex"] - s["shaft"]
        horizontal = reach * reach - d.x * d.x - d.z * d.z
        if horizontal <= 0:
            cmds.error("The apex is already out of reach horizontally; check HINGES.")
        lifts.append(-d.y + horizontal ** 0.5)
    return min(lifts)


def build():
    sides = {}
    for side, parts in HINGES.items():
        sides[side] = {k: centre(v) for k, v in parts.items()}
        sides[side]["axis"] = main_axis(parts["shaft"])

    shaft_mid = (sides["L"]["shaft"] + sides["R"]["shaft"]) * 0.5
    head_pos = (sides["L"]["apex"] + sides["R"]["apex"]) * 0.5
    lift = safe_raise(sides)

    # Controls
    main_ctrl = cmds.circle(name="main_ctrl", normal=(0, 1, 0), radius=80, ch=False)[0]
    cmds.xform(main_ctrl, ws=True, translation=tup(shaft_mid))
    colour(main_ctrl, "C")
    cmds.addAttr(main_ctrl, longName="raise", attributeType="double", min=0, max=1,
                 defaultValue=0, keyable=True)

    head_drv = cmds.group(empty=True, name="head_ctrl_drv", parent=main_ctrl)
    cmds.xform(head_drv, ws=True, translation=tup(head_pos))
    head_ctrl = box_curve("head_ctrl", 30)
    colour(head_ctrl, "C")
    cmds.parent(head_ctrl, head_drv, relative=True)
    for attr in ("tx", "tz", "rx", "ry", "rz", "sx", "sy", "sz"):
        cmds.setAttr(head_ctrl + "." + attr, lock=True, keyable=False)

    mult = cmds.createNode("multiplyDivide", name="raise_mult")
    cmds.setAttr(mult + ".input2X", lift)
    cmds.connectAttr(main_ctrl + ".raise", mult + ".input1X")
    cmds.connectAttr(mult + ".outputX", head_drv + ".translateY")

    # Joints
    cmds.select(clear=True)
    root = cmds.joint(name="root_jnt", position=tup(shaft_mid))
    for side, s in sides.items():
        cmds.select(root)
        lower = cmds.joint(name=side + "_lowerArm_jnt", position=tup(s["shaft"]))
        upper = cmds.joint(name=side + "_upperArm_jnt", position=tup(s["knee"]))
        apex = cmds.joint(name=side + "_apex_jnt", position=tup(s["apex"]))
        cmds.joint(lower, edit=True, orientJoint="xyz", secondaryAxisOrient="yup", children=True)

        # Pole vector in the plane perpendicular to the hinge, on the knee's side
        line = s["apex"] - s["shaft"]
        bend = (s["axis"] ^ line).normal()
        if (s["knee"] - (s["shaft"] + line * 0.5)) * bend < 0:
            bend = -bend
        pole = cmds.spaceLocator(name=side + "_arm_pole")[0]
        cmds.xform(pole, ws=True, translation=tup(s["knee"] + bend * POLE_DISTANCE))
        cmds.parent(pole, main_ctrl)
        cmds.setAttr(pole + ".visibility", 0)

        ik = cmds.ikHandle(name=side + "_arm_ik", startJoint=lower, endEffector=apex,
                           solver="ikRPsolver")[0]
        cmds.poleVectorConstraint(pole, ik)
        cmds.parent(ik, head_ctrl)
        cmds.setAttr(ik + ".visibility", 0)

    cmds.select(root)
    head = cmds.joint(name="head_jnt", position=tup(head_pos))
    cmds.parentConstraint(head_ctrl, head, maintainOffset=True)
    cmds.parentConstraint(main_ctrl, root, maintainOffset=True)
    print("Rig built. Head raise height: %.1f cm (%.0f%% reach cap)" % (lift, REACH_CAP * 100))


if __name__ == "__main__":
    build()
