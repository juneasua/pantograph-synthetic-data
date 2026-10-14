"""
wear_blendshapes.py

Adds the contact strip wear system and rebuilds the skin in the right order.
Each strip gets a worn copy whose carbon is ground flat: deepest in the
middle (WEAR_DEPTH) and lighter towards the ends (END_WEAR of the full
depth), like a real strip worn by the wire. The worn copy becomes a
blendShape target driven by the "wear" attribute on the strip's control.

Order matters for FBX: the blendShape must come before the skinCluster, or
the morph targets are not exported. So the script:
    1. puts the rig in its rest pose
    2. saves the joint map and unbinds (skin_map_tools.py)
    3. deletes history on the meshes
    4. builds the wear blendShapes
    5. rebinds the skin on top

Usage:
    Put this folder on Maya's Python path (needs skin_map_tools.py) and run.

Functions:
    rest_pose()        -- raise 0, wear 0, maintenance controls zeroed
    flatten(mesh)      -- grinds a mesh's top into the worn profile
    add_wear(mesh)     -- worn target + blendShape + link to the control
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

import skin_map_tools

WEAR_DEPTH = 0.6        # cm of carbon removed at the centre at wear = 1
END_WEAR = 0.3          # wear at the ends, as a fraction of the centre's
DELETE_TARGETS = True   # worn meshes aren't needed once the blendShape exists
STRIP_PATTERN = "*_contactStrip_*_geo"


def rest_pose():
    if cmds.objExists("main_ctrl.raise"):
        cmds.setAttr("main_ctrl.raise", 0)
    for ctrl in cmds.ls("*_contactStrip_*_ctrl", "*_stripClamp_*_ctrl", type="transform"):
        for attr in ("tx", "ty", "tz", "rx", "ry", "rz"):
            if cmds.getAttr(ctrl + "." + attr, settable=True):
                cmds.setAttr(ctrl + "." + attr, 0)
        if cmds.objExists(ctrl + ".wear"):
            cmds.setAttr(ctrl + ".wear", 0)


def flatten(mesh):
    sel = om.MSelectionList()
    sel.add(mesh)
    dag = sel.getDagPath(0)
    dag.extendToShape()
    fn = om.MFnMesh(dag)
    pts = fn.getPoints(om.MSpace.kWorld)

    xs, zs = [p.x for p in pts], [p.z for p in pts]
    axis = 0 if max(xs) - min(xs) >= max(zs) - min(zs) else 2  # strip's long axis
    lo = min(p[axis] for p in pts)
    hi = max(p[axis] for p in pts)
    top = max(p.y for p in pts)

    worn = om.MPointArray()
    for p in pts:
        u = (p[axis] - lo) / (hi - lo)               # 0 at one end, 1 at the other
        profile = END_WEAR + (1.0 - END_WEAR) * (1.0 - (2.0 * u - 1.0) ** 2)
        limit = top - WEAR_DEPTH * profile
        worn.append(om.MPoint(p.x, min(p.y, limit), p.z))
    fn.setPoints(worn, om.MSpace.kWorld)


def add_wear(mesh):
    target = cmds.duplicate(mesh, name=mesh.replace("_geo", "_worn"))[0]
    flatten(target)
    bs = cmds.blendShape(target, mesh, name=mesh.replace("_geo", "_wear_bs"))[0]
    ctrl = mesh.replace("_geo", "_ctrl")
    if cmds.objExists(ctrl):
        if not cmds.objExists(ctrl + ".wear"):
            cmds.addAttr(ctrl, longName="wear", attributeType="double", min=0, max=1,
                         defaultValue=0, keyable=True)
        cmds.connectAttr(ctrl + ".wear", bs + ".weight[0]", force=True)
    else:
        print("WARNING: no control %s; %s is not connected" % (ctrl, bs))

    if DELETE_TARGETS:
        cmds.delete(target)
    else:
        grp = "wear_targets_grp"
        if not cmds.objExists(grp):
            grp = cmds.group(empty=True, name=grp)
            cmds.setAttr(grp + ".visibility", 0)
        cmds.parent(target, grp)
    return bs


def main():
    rest_pose()
    mapping = skin_map_tools.unbind()
    for mesh in mapping:
        cmds.delete(mesh, constructionHistory=True)  # also removes old wear blendShapes
    strips = sorted(cmds.ls(STRIP_PATTERN, type="transform"))
    for mesh in strips:
        add_wear(mesh)
    skin_map_tools.rebind()
    print("Wear added to %d strips; skin rebuilt on top." % len(strips))


if __name__ == "__main__":
    main()
