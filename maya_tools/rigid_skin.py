"""
rigid_skin.py

Skins every low-poly part 100% to a single joint, chosen by rules from the
part's name. Mechanical parts don't bend, so each mesh follows exactly one
joint. Anything that matches no rule goes to root_jnt (the static base,
insulators and rails).

Usage:
    Run after rig_builder.py and maintenance_joints.py, in the rest pose.

Functions:
    joint_for(mesh)  -- joint name for a mesh, from RULES
    main()

Author:
    June

Changelog:
    2026-10-14  Cleaned up for portfolio release.

Environment:
    Autodesk Maya 2024, Python 3.10, maya.cmds
"""
import maya.cmds as cmds

GEO_ROOT = "geo_grp"
DEFAULT_JOINT = "root_jnt"

# (text in the mesh name, joint). {name} = mesh name without "_geo",
# {side} = its L/R/C prefix. First match wins.
RULES = [
    ("contactStrip", "{name}_jnt"),
    ("stripClamp", "{name}_jnt"),
    ("panHead", "head_jnt"),
    ("headSpring", "head_jnt"),
    ("headSuspension", "head_jnt"),
    ("apex", "{side}_apex_jnt"),
    ("knee", "{side}_upperArm_jnt"),
    ("upperArm", "{side}_upperArm_jnt"),
    ("lowerArm", "{side}_lowerArm_jnt"),
    ("mainShaft", "{side}_lowerArm_jnt"),
    ("shaftSleeve", "{side}_lowerArm_jnt"),
]


def joint_for(mesh):
    name = mesh[:-4] if mesh.endswith("_geo") else mesh
    side = name.split("_")[0]
    for text, pattern in RULES:
        if text.lower() in name.lower():
            jnt = pattern.format(name=name, side=side)
            if cmds.objExists(jnt):
                return jnt
            print("WARNING: %s wants %s, which doesn't exist; using %s" % (mesh, jnt, DEFAULT_JOINT))
            break
    return DEFAULT_JOINT


def main():
    nodes = cmds.listRelatives(GEO_ROOT, allDescendents=True, type="transform") or []
    meshes = [n for n in nodes if cmds.listRelatives(n, shapes=True, type="mesh")]
    for mesh in meshes:
        if cmds.ls(cmds.listHistory(mesh) or [], type="skinCluster"):
            continue  # already skinned
        jnt = joint_for(mesh)
        cmds.skinCluster(jnt, mesh, toSelectedBones=True, bindMethod=0,
                         maximumInfluences=1, name=mesh + "_skin")
        print("%-35s -> %s" % (mesh, jnt))
    print("Rigid skin done on %d meshes." % len(meshes))


if __name__ == "__main__":
    main()
