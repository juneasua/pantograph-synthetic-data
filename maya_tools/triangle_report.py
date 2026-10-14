"""
triangle_report.py

Lists the visible CAD reference parts ("cad_*") ranked by triangle count.
Hide each CAD part once it has been rebuilt, and the report becomes a
to-do list of what is left to optimise.

Functions:
    triangle_rows() -- (triangles, name) for every visible cad_ mesh
    main()          -- prints the ranking and the remaining total

Author:
    June

Changelog:
    2026-10-14  Cleaned up for portfolio release.

Environment:
    Autodesk Maya 2024, Python 3.10, maya.cmds
"""
import maya.cmds as cmds


def triangle_rows():
    rows = []
    for t in cmds.ls("cad_*", type="transform"):
        if not cmds.getAttr(t + ".visibility"):
            continue
        shapes = cmds.listRelatives(t, shapes=True, type="mesh") or []
        if shapes:
            rows.append((cmds.polyEvaluate(shapes[0], triangle=True), t))
    rows.sort(reverse=True)
    return rows


def main():
    rows = triangle_rows()
    total = sum(r[0] for r in rows)
    for tris, name in rows:
        share = 100.0 * tris / total if total else 0.0
        print("%9d  %5.1f%%  %s" % (tris, share, name))
    print("Remaining: %d tris in %d parts" % (total, len(rows)))


if __name__ == "__main__":
    main()
