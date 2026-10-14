"""
icp_align.py

Snaps a hand-built low-poly piece onto its CAD reference with Iterative
Closest Point (ICP). Each step pairs the piece's points with the closest
points on the reference, keeps the best 80% of matches, computes the best
rigid rotation with Horn's quaternion method, and applies it. Stops when the
average gap stops improving. Moves and rotates only (no scaling).

Usage:
    Select the low-poly piece first, then the reference part(s), and run.
    Ctrl+Z undoes the whole alignment.

Functions:
    mesh_fn(node)                     -- MFnMesh of a transform
    sample_points(fn)                 -- vertices plus triangle centres
    closest_on_targets(p, targets)    -- nearest point on any reference
    best_rotation(src, dst)           -- Horn's method, as an MQuaternion
    align(piece, refs)                -- the ICP loop, returns the final gap
    main()                            -- runs on the selection

Author:
    June

Changelog:
    2026-10-14  Cleaned up for portfolio release.

Environment:
    Autodesk Maya 2024, Python 3.10, maya.cmds, maya.api.OpenMaya
"""
import maya.cmds as cmds
import maya.api.OpenMaya as om

ITERATIONS = 40
KEEP = 0.8  # use the best 80% of matches each step (ignores areas the retopo simplified)


def mesh_fn(node):
    sel = om.MSelectionList()
    sel.add(node)
    dag = sel.getDagPath(0)
    dag.extendToShape()
    return om.MFnMesh(dag)


def sample_points(fn):
    """World-space vertices plus triangle centres of the low-poly piece."""
    pts = [om.MVector(p) for p in fn.getPoints(om.MSpace.kWorld)]
    _, tv = fn.getTriangles()
    centres = [(pts[tv[i]] + pts[tv[i + 1]] + pts[tv[i + 2]]) * (1.0 / 3.0)
               for i in range(0, len(tv), 3)]
    return pts + centres


def closest_on_targets(p, targets):
    best, best_d = None, None
    for fn in targets:
        q = om.MVector(fn.getClosestPoint(om.MPoint(p), om.MSpace.kWorld)[0])
        d = (q - p).length()
        if best_d is None or d < best_d:
            best, best_d = q, d
    return best, best_d


def best_rotation(src, dst):
    """Horn's method: the rotation that best maps src onto dst (both centred)."""
    S = [[0.0] * 3 for _ in range(3)]
    for a, b in zip(src, dst):
        av, bv = (a.x, a.y, a.z), (b.x, b.y, b.z)
        for i in range(3):
            for j in range(3):
                S[i][j] += av[i] * bv[j]
    (xx, xy, xz), (yx, yy, yz), (zx, zy, zz) = S
    N = [[xx + yy + zz, yz - zy, zx - xz, xy - yx],
         [yz - zy, xx - yy - zz, xy + yx, zx + xz],
         [zx - xz, xy + yx, -xx + yy - zz, yz + zy],
         [xy - yx, zx + xz, yz + zy, -xx - yy + zz]]
    shift = max(sum(abs(v) for v in row) for row in N) + 1e-9  # keeps eigenvalues positive
    for i in range(4):
        N[i][i] += shift
    q = [1.0, 0.0, 0.0, 0.0]
    for _ in range(200):
        q = [sum(N[i][k] * q[k] for k in range(4)) for i in range(4)]
        n = sum(v * v for v in q) ** 0.5
        q = [v / n for v in q]
    w, x, y, z = q
    return om.MQuaternion(x, y, z, w)


def align(piece, refs, iterations=ITERATIONS, verbose=True):
    low = mesh_fn(piece)
    targets = [mesh_fn(r) for r in refs]
    prev, step = None, 0
    for step in range(iterations):
        pairs = []
        for p in sample_points(low):
            q, d = closest_on_targets(p, targets)
            pairs.append((d, p, q))
        pairs.sort(key=lambda t: t[0])
        pairs = pairs[:max(3, int(len(pairs) * KEEP))]
        rms = (sum(d * d for d, _, _ in pairs) / len(pairs)) ** 0.5
        if prev is not None and abs(prev - rms) < 1e-5:
            break
        prev = rms

        ps = [p for _, p, _ in pairs]
        qs = [q for _, _, q in pairs]
        pc = sum(ps, om.MVector()) * (1.0 / len(ps))
        qc = sum(qs, om.MVector()) * (1.0 / len(qs))
        rot = best_rotation([p - pc for p in ps], [q - qc for q in qs])

        # Rotate around the piece's centre, then move that centre onto the target's
        pc_rot = om.MVector(om.MPoint(pc) * rot.asMatrix())
        tm = om.MTransformationMatrix()
        tm.setRotation(rot)
        tm.setTranslation(qc - pc_rot, om.MSpace.kTransform)
        world = om.MMatrix(cmds.xform(piece, q=True, ws=True, matrix=True)) * tm.asMatrix()
        cmds.xform(piece, ws=True,
                   matrix=[world.getElement(r, c) for r in range(4) for c in range(4)])

    if verbose:
        print("%s aligned after %d steps, average gap %.4f cm" % (piece, step + 1, prev))
    return prev


def main():
    sel = cmds.ls(sl=True, type="transform")
    if len(sel) < 2:
        cmds.error("Select your low-poly piece first, then the reference part(s).")
    cmds.undoInfo(openChunk=True)
    try:
        align(sel[0], sel[1:])
    finally:
        cmds.undoInfo(closeChunk=True)


if __name__ == "__main__":
    main()
