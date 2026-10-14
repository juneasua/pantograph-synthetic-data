"""
fbx_export.py

Exports the rig to FBX for Unreal with every FBX option set explicitly, so
each export is reproducible and doesn't depend on whatever was last chosen in
the export dialog. Exports skin, blendShapes (as morph targets), smoothing
groups and tangents; with ANIMATION = True it also bakes the animation.

Usage:
    Set ANIMATION and the paths, then run.
    Static rig:  ANIMATION = False -> pantograph_rig.fbx
    Animation:   ANIMATION = True  -> pantograph_maintenance_anim.fbx

Functions:
    set_options(animation)  -- every FBX export flag
    main()

Author:
    June

Changelog:
    2026-10-14  Cleaned up for portfolio release.

Environment:
    Autodesk Maya 2024, Python 3.10, maya.cmds, maya.mel, fbxmaya plugin
"""
import maya.cmds as cmds
import maya.mel as mel

ANIMATION = False
START, END = 0, 530
EXPORT_NODES = ["root_jnt", "geo_grp"]
FOLDER = r"C:\Users\june\Documents\maya\projects\SIT_Portfolio\assets"
STATIC_FILE = "pantograph_rig.fbx"
ANIM_FILE = "pantograph_maintenance_anim.fbx"


def set_options(animation):
    flags = [
        "FBXResetExport",
        "FBXExportFileVersion -v FBX202000",
        "FBXExportInAscii -v false",
        "FBXExportUpAxis y",
        "FBXExportScaleFactor 1.0",
        "FBXExportConvertUnitString cm",
        "FBXExportSmoothingGroups -v true",
        "FBXExportHardEdges -v false",
        "FBXExportTangents -v true",
        "FBXExportSmoothMesh -v false",
        "FBXExportTriangulate -v false",
        "FBXExportSkins -v true",
        "FBXExportShapes -v true",
        "FBXExportSkeletonDefinitions -v false",
        "FBXExportInputConnections -v false",
        "FBXExportConstraints -v false",
        "FBXExportCameras -v false",
        "FBXExportLights -v false",
        "FBXExportEmbeddedTextures -v false",
        "FBXExportAnimationOnly -v false",
        "FBXExportBakeComplexAnimation -v %s" % ("true" if animation else "false"),
    ]
    if animation:
        flags += [
            "FBXExportBakeComplexStart -v %d" % START,
            "FBXExportBakeComplexEnd -v %d" % END,
            "FBXExportBakeComplexStep -v 1",
            "FBXExportBakeResampleAnimation -v true",
        ]
    for flag in flags:
        mel.eval(flag)


def main():
    if not cmds.pluginInfo("fbxmaya", query=True, loaded=True):
        cmds.loadPlugin("fbxmaya")
    if cmds.objExists("wear_targets_grp"):
        cmds.warning("wear_targets_grp exists: delete it first, or the worn meshes "
                     "are imported as extra meshes.")
    missing = [n for n in EXPORT_NODES if not cmds.objExists(n)]
    if missing:
        cmds.error("Missing: " + ", ".join(missing))

    set_options(ANIMATION)
    path = (FOLDER + "\\" + (ANIM_FILE if ANIMATION else STATIC_FILE)).replace("\\", "/")
    cmds.select(EXPORT_NODES, replace=True)
    mel.eval('FBXExport -f "%s" -s' % path)
    print("Exported " + path)


if __name__ == "__main__":
    main()
