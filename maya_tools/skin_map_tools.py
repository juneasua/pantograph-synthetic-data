"""
skin_map_tools.py

Saves which joint each rigidly skinned mesh follows, unbinds everything, and
rebinds it later exactly as it was. Used whenever the geometry has to change
after skinning (for example to add blendshapes, which must sit before the
skin in the deformer stack for FBX to export them as morph targets).

The joint map is stored in the scene itself, on a network node, so it
survives saving and reopening.

Usage:
    Set MODE to "unbind" or "rebind" and run.

Functions:
    save_map()  -- {mesh: joint} for every skinned mesh, stored in the scene
    load_map()  -- reads the stored map
    unbind()    -- saves the map, then removes every skinCluster
    rebind()    -- rigid-skins each mesh back to its saved joint

Author:
    June

Changelog:
    2026-10-14  Cleaned up for portfolio release.

Environment:
    Autodesk Maya 2024, Python 3.10, maya.cmds
"""
import json

import maya.cmds as cmds

MODE = "unbind"  # "unbind" or "rebind"
DATA_NODE = "skin_map_data"


def main_joint(skin, mesh):
    influences = cmds.skinCluster(skin, query=True, influence=True)
    if len(influences) == 1:
        return influences[0]
    weights = cmds.skinPercent(skin, mesh + ".vtx[0]", query=True, value=True)
    return influences[weights.index(max(weights))]


def save_map():
    mapping = {}
    for skin in cmds.ls(type="skinCluster"):
        for shape in cmds.skinCluster(skin, query=True, geometry=True) or []:
            mesh = cmds.listRelatives(shape, parent=True)[0]
            mapping[mesh] = main_joint(skin, mesh)
    if not cmds.objExists(DATA_NODE):
        cmds.createNode("network", name=DATA_NODE)
        cmds.addAttr(DATA_NODE, longName="skinMap", dataType="string")
    cmds.setAttr(DATA_NODE + ".skinMap", json.dumps(mapping), type="string")
    print("Saved joint map for %d meshes." % len(mapping))
    return mapping


def load_map():
    if not cmds.objExists(DATA_NODE):
        cmds.error("No saved skin map in this scene. Run unbind first.")
    return json.loads(cmds.getAttr(DATA_NODE + ".skinMap"))


def unbind():
    mapping = save_map()
    for skin in cmds.ls(type="skinCluster"):
        cmds.skinCluster(skin, edit=True, unbind=True)
    print("Unbound %d meshes." % len(mapping))
    return mapping


def rebind():
    mapping = load_map()
    for mesh, jnt in sorted(mapping.items()):
        if cmds.ls(cmds.listHistory(mesh) or [], type="skinCluster"):
            continue
        # A new skinCluster is added on top of any existing blendShape,
        # which is the order FBX needs for morph targets.
        cmds.skinCluster(jnt, mesh, toSelectedBones=True, bindMethod=0,
                         maximumInfluences=1, name=mesh + "_skin")
    print("Rebound %d meshes." % len(mapping))


if __name__ == "__main__":
    if MODE == "unbind":
        unbind()
    elif MODE == "rebind":
        rebind()
    else:
        cmds.error('MODE must be "unbind" or "rebind".')
