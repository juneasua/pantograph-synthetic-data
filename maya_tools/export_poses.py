"""
export_poses.py

Exports the pantograph at several raise positions as OBJ files for the
synthetic dataset. Each part keeps its name as an OBJ group, so the dataset
script can label every part from its name. Strips are exported new
(wear = 0); the dataset script applies random wear itself.

Usage:
    Set FOLDER and RAISE_VALUES, then run. Writes pantograph_raise_000.obj,
    pantograph_raise_015.obj, and so on.

Functions:
    set_pose(value)  -- raise value, all strips new
    main()

Author:
    June

Changelog:
    2026-10-14  Cleaned up for portfolio release.

Environment:
    Autodesk Maya 2024, Python 3.10, maya.cmds, objExport plugin
"""
import maya.cmds as cmds

FOLDER = r"C:\Users\june\Documents\maya\projects\SIT_Portfolio\images\poses"
RAISE_VALUES = [0.0, 0.15, 0.30, 0.50, 0.65]
GEO_ROOT = "geo_grp"
OPTIONS = "groups=1;ptgroups=1;materials=0;smoothing=1;normals=1"


def set_pose(value):
    cmds.setAttr("main_ctrl.raise", value)
    for ctrl in cmds.ls("*_contactStrip_*_ctrl", type="transform"):
        if cmds.objExists(ctrl + ".wear"):
            cmds.setAttr(ctrl + ".wear", 0)


def main():
    if not cmds.pluginInfo("objExport", query=True, loaded=True):
        cmds.loadPlugin("objExport")
    original = cmds.getAttr("main_ctrl.raise")
    try:
        for value in RAISE_VALUES:
            set_pose(value)
            path = "%s/pantograph_raise_%03d.obj" % (FOLDER.replace("\\", "/"), round(value * 100))
            cmds.select(GEO_ROOT, replace=True)
            cmds.file(path, force=True, exportSelected=True, type="OBJexport", options=OPTIONS)
            print("Exported " + path)
    finally:
        cmds.setAttr("main_ctrl.raise", original)


if __name__ == "__main__":
    main()
