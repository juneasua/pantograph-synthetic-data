import blenderproc as bproc  # must be the first import
import argparse
import glob
import json
import os
import random

import bpy
import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument("poses_dir")
parser.add_argument("output_dir")
parser.add_argument("--textures", default="")              # folder with the Blender texture export
parser.add_argument("--textured_share", type=float, default=0.5)
parser.add_argument("--views", type=int, default=5)
parser.add_argument("--seed", type=int, default=0)
args = parser.parse_args()

random.seed(args.seed)
np.random.seed(args.seed)
bproc.init()

CLASSES = {"contact_strip": 1, "pan_head": 2, "head_suspension": 3, "upper_frame": 4,
           "lower_frame": 5, "insulator": 6, "base": 7}
RULES = [  # (text in the object name, class) - first match wins, anything else is "base"
    ("contactStrip", "contact_strip"),
    ("headSuspension", "head_suspension"), ("headSpring", "head_suspension"),
    ("panFrame", "pan_head"), ("panHeadFrame", "pan_head"),
    ("stripClamp", "pan_head"), ("apexBearing", "pan_head"),
    ("lowerArm", "lower_frame"), ("mainShaft", "lower_frame"),
    ("upperArm", "upper_frame"), ("upperFrameLeg", "upper_frame"), ("knee", "upper_frame"),
    ("apexTube", "upper_frame"), ("apexFitting", "upper_frame"),
    ("rodEndFitting", "upper_frame"), ("rodClamp", "upper_frame"),
    ("insulator_", "insulator"),
]
TEXTURE_SETS = {"head": "M_head", "frames": "M_frames", "base": "M_base"}  # Maya group -> texture set
WEAR_DEPTH = 0.6  # at wear = 1: fraction of the strip's height worn away in the middle
END_WEAR = 0.3    # wear at the strip ends, relative to the middle


def classify(name):
    for key, cls in RULES:
        if key in name:
            return cls
    return "base"


def texture_set_of(name):
    tokens = name.replace("|", " ").split()
    for key, set_name in TEXTURE_SETS.items():
        if key in tokens:
            return set_name
    return None


def grey(lo, hi, tint=0.05):
    g = random.uniform(lo, hi)
    return [min(1.0, max(0.0, g + random.uniform(-tint, tint))) for _ in range(3)] + [1.0]


def make_material(cls):
    mat = bproc.material.create("mat_" + cls)
    if cls == "insulator":
        if random.random() < 0.7:
            color = grey(0.75, 0.95, 0.03)  # white porcelain
        else:
            color = [random.uniform(0.25, 0.45), random.uniform(0.12, 0.25),
                     random.uniform(0.05, 0.12), 1.0]  # brown glaze
        metallic, rough = 0.0, random.uniform(0.05, 0.35)
    elif cls == "contact_strip":
        color, metallic, rough = grey(0.03, 0.15, 0.02), 0.0, random.uniform(0.5, 0.9)  # carbon
    elif random.random() < 0.5:  # bare or galvanised steel
        color, metallic, rough = grey(0.35, 0.75), random.uniform(0.7, 1.0), random.uniform(0.25, 0.75)
    else:  # painted steel, from a realistic palette with slight variation
        paints = [(0.45, 0.08, 0.06), (0.35, 0.36, 0.38), (0.55, 0.55, 0.52),
                  (0.12, 0.25, 0.15), (0.05, 0.05, 0.05), (0.60, 0.45, 0.08)]
        base = random.choice(paints)
        color = [min(1.0, max(0.0, c + random.uniform(-0.04, 0.04))) for c in base] + [1.0]
        metallic, rough = 0.0, random.uniform(0.35, 0.9)
    mat.set_principled_shader_value("Base Color", color)
    mat.set_principled_shader_value("Metallic", metallic)
    mat.set_principled_shader_value("Roughness", rough)
    return mat


def find_map(set_name, keywords):
    for path in sorted(glob.glob(os.path.join(args.textures, "*" + set_name + "*"))):
        low = os.path.basename(path).lower()
        if any(k in low for k in keywords):
            return path
    return None


def textured_material(set_name):
    """Principled material built from the Painter export of one texture set."""
    mat = bpy.data.materials.new("tex_" + set_name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")

    def tex(keywords, colorspace):
        path = find_map(set_name, keywords)
        if not path:
            print("  missing '%s' map for %s" % (keywords[0], set_name))
            return None
        node = nt.nodes.new("ShaderNodeTexImage")
        node.image = bpy.data.images.load(path, check_existing=True)
        node.image.colorspace_settings.name = colorspace
        return node

    bc = tex(["basecolor", "base_color", "albedo", "diffuse"], "sRGB")
    if bc:
        nt.links.new(bc.outputs["Color"], bsdf.inputs["Base Color"])
    for keywords, socket in ((["metallic", "metalness"], "Metallic"), (["roughness"], "Roughness")):
        node = tex(keywords, "Non-Color")
        if node:
            nt.links.new(node.outputs["Color"], bsdf.inputs[socket])
    nrm = tex(["normal"], "Non-Color")
    if nrm:
        nmap = nt.nodes.new("ShaderNodeNormalMap")
        nt.links.new(nrm.outputs["Color"], nmap.inputs["Color"])
        nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
    return bproc.types.Material(mat)


def apply_wear(obj, w):
    """Flatten the top of a strip, deepest in the middle."""
    o = obj.blender_obj
    mw, inv = o.matrix_world, o.matrix_world.inverted()
    pts = [mw @ v.co for v in o.data.vertices]
    top, bottom = max(p.z for p in pts), min(p.z for p in pts)
    span_x = max(p.x for p in pts) - min(p.x for p in pts)
    span_y = max(p.y for p in pts) - min(p.y for p in pts)
    axis = 0 if span_x > span_y else 1
    lo, hi = min(p[axis] for p in pts), max(p[axis] for p in pts)
    mid, half = (lo + hi) / 2.0, (hi - lo) / 2.0
    for v, p in zip(o.data.vertices, pts):
        t = abs(p[axis] - mid) / half if half else 0.0
        cut = top - WEAR_DEPTH * (top - bottom) * w * (1.0 - (1.0 - END_WEAR) * t * t)
        if p.z > cut:
            p.z = cut
            v.co = inv @ p
    o.data.update()


def bbox(objs):
    corners = np.concatenate([o.get_bound_box() for o in objs])
    return corners.min(axis=0), corners.max(axis=0)


# --- 1. Load a random pose, drop the wear targets, cm -> m ---
pose_file = random.choice(sorted(glob.glob(os.path.join(args.poses_dir, "*.obj"))))
try:
    objs = bproc.loader.load_obj(pose_file, use_split_groups=True)
except TypeError:
    objs = bproc.loader.load_obj(pose_file)
keep = []
for o in objs:
    if "_worn" in o.get_name():
        o.delete()
    else:
        keep.append(o)
objs = keep
for o in objs:
    o.set_scale([0.01, 0.01, 0.01])
bpy.context.view_layer.update()

# --- 2. Classes, materials (textured or randomised), wear ---
textured = bool(args.textures) and random.random() < args.textured_share
class_mats = {cls: make_material(cls) for cls in CLASSES}
tex_mats = {s: textured_material(s) for s in TEXTURE_SETS.values()} if textured else {}

wear, counts, head_parts = {}, {}, []
for o in objs:
    name = o.get_name()
    cls = classify(name)
    counts[cls] = counts.get(cls, 0) + 1
    o.set_cp("category_id", CLASSES[cls])
    o.clear_materials()
    o.add_material(tex_mats.get(texture_set_of(name)) or class_mats[cls])
    if cls in ("contact_strip", "pan_head"):
        head_parts.append(o)
    if cls == "contact_strip":
        w = round(random.random(), 3)
        apply_wear(o, w)
        wear[name] = w
print("Pose: %s | textured: %s | objects per class: %s"
      % (os.path.basename(pose_file), textured, counts))

lo, hi = bbox(objs)
center, size = (lo + hi) / 2.0, float(np.max(hi - lo))
head_center = np.mean(bbox(head_parts), axis=0) if head_parts else center

# --- 3. Environment: roof, copper contact wire, lights, sky ---
roof = bproc.object.create_primitive("PLANE")
roof.set_scale([size * 3, size * 3, 1])
roof.set_location([center[0], center[1], lo[2] - 0.01])
roof_mat = bproc.material.create("mat_roof")
roof_mat.set_principled_shader_value("Base Color", grey(0.1, 0.6, 0.1))
roof_mat.set_principled_shader_value("Roughness", random.uniform(0.4, 1.0))
roof.add_material(roof_mat)
roof.set_cp("category_id", 0)

wire = bproc.object.create_primitive("CYLINDER", radius=0.006, depth=size * 4,
                                     rotation=(0, np.pi / 2, 0))
wire.set_location([center[0], head_center[1] + random.uniform(-0.3, 0.3),
                   hi[2] + random.uniform(0.0, 1.5)])
wire_mat = bproc.material.create("mat_wire")
wire_mat.set_principled_shader_value("Base Color", [random.uniform(0.55, 0.75),
                                                    random.uniform(0.30, 0.40),
                                                    random.uniform(0.18, 0.25), 1.0])
wire_mat.set_principled_shader_value("Metallic", 1.0)
wire_mat.set_principled_shader_value("Roughness", random.uniform(0.3, 0.6))
wire.add_material(wire_mat)
wire.set_cp("category_id", 0)

sun = bproc.types.Light()
sun.set_type("SUN")
sun.set_rotation_euler([np.radians(random.uniform(10, 70)), 0,
                        np.radians(random.uniform(0, 360))])
sun.set_energy(random.uniform(1.0, 4.0))
fill = bproc.types.Light()
fill.set_type("POINT")
fill.set_location(center + np.random.uniform([-4, -4, 2], [4, 4, 6]))
fill.set_energy(random.uniform(50, 500))
bproc.renderer.set_world_background(
    [random.uniform(0.3, 0.9), random.uniform(0.4, 0.9), random.uniform(0.6, 1.0)],
    strength=random.uniform(0.2, 0.8))
scene = bpy.context.scene
scene.view_settings.exposure = random.uniform(-1.0, 0.3)  # some darker, some brighter shots
try:
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"  # closer to Painter's preview
except TypeError:
    pass

# --- 4. Cameras: wide shots and head close-ups ---
bproc.camera.set_resolution(960, 540)
for _ in range(args.views):
    if random.random() < 0.4:  # close-up on the head and strips
        target, radius = head_center, random.uniform(0.6, 1.0) * size
        elevation = np.radians(random.uniform(20, 75))
    else:
        target, radius = center, random.uniform(1.2, 2.5) * size
        elevation = np.radians(random.uniform(10, 70))
    azimuth = np.radians(random.uniform(0, 360))
    loc = target + radius * np.array([np.cos(elevation) * np.cos(azimuth),
                                      np.cos(elevation) * np.sin(azimuth),
                                      np.sin(elevation)])
    poi = target + np.random.uniform(-0.1, 0.1, 3) * size
    rot = bproc.camera.rotation_from_forward_vec(poi - loc,
                                                 inplane_rot=np.radians(random.uniform(-10, 10)))
    bproc.camera.add_camera_pose(bproc.math.build_transformation_mat(loc, rot))

# --- 5. Render and write COCO + wear labels ---
bproc.renderer.set_max_amount_of_samples(64)
bproc.renderer.enable_segmentation_output(map_by=["category_id", "instance", "name"],
                                          default_values={"category_id": 0})
data = bproc.renderer.render()

coco_dir = os.path.join(args.output_dir, "coco_data")
img_dir = os.path.join(coco_dir, "images")
start = len(os.listdir(img_dir)) if os.path.isdir(img_dir) else 0

try:
    mapping = bproc.utility.LabelIdMapping.from_dict(dict({"background": 0}, **CLASSES))
except AttributeError:
    mapping = None
bproc.writer.write_coco_annotations(coco_dir,
                                    instance_segmaps=data["instance_segmaps"],
                                    instance_attribute_maps=data["instance_attribute_maps"],
                                    colors=data["colors"], color_file_format="JPEG",
                                    label_mapping=mapping, append_to_existing_output=True)

with open(os.path.join(args.output_dir, "wear_labels.jsonl"), "a") as f:
    for i in range(args.views):
        f.write(json.dumps({"image": "images/%06d.jpg" % (start + i),
                            "pose": os.path.basename(pose_file), "textured": textured,
                            "seed": args.seed, "wear": wear}) + "\n")
print("Wrote %d images starting at %d" % (args.views, start))