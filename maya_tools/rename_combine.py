"""
rename_combine.py

Renames the finished low-poly parts to the "X_partName_geo" convention and
merges the sub-pieces that belong to one part. The side letter comes from
each part's world X position: L = +X, R = -X, C = centred. Parts of the same
type and side are numbered front to back (01, 02...), unless the type is in
COMBINE, in which case they are merged into a single mesh.

Usage:
    Edit RULES to match the names in your scene, run once with DRY_RUN = True
    to check the plan in the Script Editor, then set DRY_RUN = False and run.

Functions:
    part_type(node)   -- part name from RULES, or None
    side_of(node)     -- "L", "R" or "C" from world X position
    plan()            -- {(side, part): [nodes]} plus unmatched nodes
    main()            -- prints the plan and applies it unless DRY_RUN

Author:
    June

Changelog:
    2026-10-14  Cleaned up for portfolio release.

Environment:
    Autodesk Maya 2024, Python 3.10, maya.cmds
"""
import maya.cmds as cmds

DRY_RUN = True
GEO_ROOT = "geo_grp"   # group holding the low-poly parts
SIDE_TOLERANCE = 1.0   # cm from X = 0 still counted as centred

# (text found in the current name, part name). First match wins, so put
# specific words before general ones.
RULES = [
    ("contactStrip", "contactStrip"),
    ("stripClamp", "stripClamp"),
    ("horn", "panHeadHorn"),
    ("panHead", "panHead"),
    ("spring", "headSpring"),
    ("suspension", "headSuspension"),
    ("apexTube", "apexTube"),
    ("apexFitting", "apexFitting"),
    ("knee", "knee"),
    ("upperArm", "upperArm"),
    ("lowerArm", "lowerArm"),
    ("shaft", "mainShaft"),
    ("sleeve", "shaftSleeve"),
    ("insulator", "insulator"),
    ("restStop", "restStop"),
    ("rail", "baseRail"),
    ("base", "baseFrame"),
]

# Part types whose pieces (per side) are merged into one mesh
COMBINE = {"baseFrame", "panHead", "headSuspension"}


def mesh_transforms(root):
    nodes = cmds.listRelatives(root, allDescendents=True, type="transform", fullPath=True) or []
    return [n for n in nodes if cmds.listRelatives(n, shapes=True, type="mesh")]


def part_type(node):
    short = node.split("|")[-1].lower()
    for text, part in RULES:
        if text.lower() in short:
            return part
    return None


def centre(node):
    bb = cmds.exactWorldBoundingBox(node)
    return ((bb[0] + bb[3]) / 2.0, (bb[1] + bb[4]) / 2.0, (bb[2] + bb[5]) / 2.0)


def side_of(node):
    x = centre(node)[0]
    if x > SIDE_TOLERANCE:
        return "L"
    if x < -SIDE_TOLERANCE:
        return "R"
    return "C"


def plan():
    groups, unmatched = {}, []
    for node in mesh_transforms(GEO_ROOT):
        part = part_type(node)
        if part is None:
            unmatched.append(node)
            continue
        groups.setdefault((side_of(node), part), []).append(node)
    for nodes in groups.values():
        nodes.sort(key=lambda n: (centre(n)[2], centre(n)[1]))  # front to back
    return groups, unmatched


def main():
    groups, unmatched = plan()
    actions = []
    for (side, part), nodes in sorted(groups.items()):
        if part in COMBINE and len(nodes) > 1:
            actions.append(("combine", nodes, "%s_%s_geo" % (side, part)))
        elif len(nodes) == 1:
            actions.append(("rename", nodes, "%s_%s_geo" % (side, part)))
        else:
            for i, node in enumerate(nodes, start=1):
                actions.append(("rename", [node], "%s_%s_%02d_geo" % (side, part, i)))

    for kind, nodes, new in actions:
        print("%-8s %-40s <- %s" % (kind, new, ", ".join(n.split("|")[-1] for n in nodes)))
    for node in unmatched:
        print("NO RULE  %s" % node.split("|")[-1])
    if DRY_RUN:
        print("Dry run only. Set DRY_RUN = False to apply.")
        return

    cmds.undoInfo(openChunk=True)
    try:
        # Temporary names first, so new names never clash with old ones
        temp = []
        for k, (kind, nodes, new) in enumerate(actions):
            renamed = [cmds.rename(n, "tmp_%03d_%02d" % (k, i)) for i, n in enumerate(nodes)]
            temp.append((kind, renamed, new))
        for kind, nodes, new in temp:
            if kind == "rename":
                cmds.rename(nodes[0], new)
            else:
                parent = cmds.listRelatives(nodes[0], parent=True)
                merged = cmds.polyUnite(nodes, name=new, mergeUVSets=True, ch=False)[0]
                for n in nodes:
                    if cmds.objExists(n):
                        cmds.delete(n)
                if parent:
                    cmds.parent(merged, parent[0])
    finally:
        cmds.undoInfo(closeChunk=True)
    print("Renamed and combined %d parts." % len(actions))


if __name__ == "__main__":
    main()
