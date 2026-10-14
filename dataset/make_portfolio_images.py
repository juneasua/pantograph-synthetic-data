import json
import os
import random

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pycocotools import mask as mask_utils

DATA = r"C:\Users\june\Documents\SIT_dataset\output\coco_data"
OUT = r"C:\Users\june\Documents\SIT_dataset\portfolio_images"
SEED = 7
BOX_CLASSES = {"contact_strip", "insulator"}  # boxes drawn only for these, to keep it readable
COLORS = {"contact_strip": (230, 57, 70), "pan_head": (244, 162, 97),
          "head_suspension": (233, 196, 106), "upper_frame": (42, 157, 143),
          "lower_frame": (69, 123, 157), "insulator": (168, 218, 220),
          "base": (131, 56, 236)}

os.makedirs(OUT, exist_ok=True)
random.seed(SEED)
coco = json.load(open(os.path.join(DATA, "coco_annotations.json")))
cats = {c["id"]: c["name"] for c in coco["categories"]}
anns_by_img = {}
for a in coco["annotations"]:
    anns_by_img.setdefault(a["image_id"], []).append(a)
images = coco["images"]
try:
    FONT = ImageFont.truetype("arial.ttf", 18)
except OSError:
    FONT = ImageFont.load_default()


def decode(a, h, w):
    seg = a["segmentation"]
    if isinstance(seg, dict):
        rle = mask_utils.frPyObjects(seg, h, w) if isinstance(seg["counts"], list) else seg
    else:
        rle = mask_utils.merge(mask_utils.frPyObjects(seg, h, w))
    return mask_utils.decode(rle).astype(bool)


def render(img):
    return Image.open(os.path.join(DATA, img["file_name"])).convert("RGB")


def class_mask(img):
    h, w = img["height"], img["width"]
    canvas = np.zeros((h, w, 3), np.uint8)
    for a in sorted(anns_by_img.get(img["id"], []), key=lambda a: -a["area"]):
        name = cats.get(a["category_id"])
        if name in COLORS:
            canvas[decode(a, h, w)] = COLORS[name]
    return Image.fromarray(canvas)


def overlay(img):
    base = np.asarray(render(img)).astype(float)
    mask = np.asarray(class_mask(img)).astype(float)
    hit = mask.sum(axis=2) > 0
    out = base.copy()
    out[hit] = 0.5 * base[hit] + 0.5 * mask[hit]
    pic = Image.fromarray(out.astype(np.uint8))
    draw = ImageDraw.Draw(pic)
    for a in anns_by_img.get(img["id"], []):
        name = cats.get(a["category_id"])
        if name in BOX_CLASSES:
            x, y, w, h = a["bbox"]
            draw.rectangle([x, y, x + w, y + h], outline=COLORS[name], width=3)
    return pic


def legend(width):
    bar = Image.new("RGB", (width, 60), (24, 24, 24))
    draw = ImageDraw.Draw(bar)
    x = 20
    for name, col in COLORS.items():
        draw.rectangle([x, 20, x + 20, 40], fill=col)
        draw.text((x + 28, 19), name, fill=(235, 235, 235), font=FONT)
        x += 30 + int(draw.textlength(name, font=FONT)) + 24
    return bar


def strip_area(img):
    return sum(a["area"] for a in anns_by_img.get(img["id"], [])
               if cats.get(a["category_id"]) == "contact_strip")


def square(pic):
    w, h = pic.size
    s = min(w, h)
    return pic.crop(((w - s) // 2, (h - s) // 2, (w + s) // 2, (h + s) // 2))


# Best close-ups (largest visible contact strips) for the cover and examples
close = sorted(images, key=strip_area, reverse=True)[:30]
random.shuffle(close)

# 1. Cover: 2 renders + their masks, square
cover = Image.new("RGB", (1080, 1080))
for row, img in enumerate(close[:2]):
    cover.paste(square(render(img)).resize((540, 540)), (0, row * 540))
    cover.paste(square(class_mask(img)).resize((540, 540)), (540, row * 540))
cover.save(os.path.join(OUT, "00_cover.jpg"), quality=95)

# 2. Render grid: 16 random renders
grid = Image.new("RGB", (1920, 1080))
for k, img in enumerate(random.sample(images, 16)):
    grid.paste(render(img).resize((480, 270)), ((k % 4) * 480, (k // 4) * 270))
grid.save(os.path.join(OUT, "01_render_grid.jpg"), quality=95)

# 3. Examples: render | mask | overlay, with a legend
for n, img in enumerate(close[2:5], start=1):
    panel = Image.new("RGB", (1920, 360 + 60), (24, 24, 24))
    for col, pic in enumerate((render(img), class_mask(img), overlay(img))):
        panel.paste(pic.resize((640, 360)), (col * 640, 0))
    panel.paste(legend(1920), (0, 360))
    panel.save(os.path.join(OUT, "02_example_%d.jpg" % n), quality=95)

# 4. Instances per class
counts = {name: 0 for name in COLORS}
for a in coco["annotations"]:
    name = cats.get(a["category_id"])
    if name in counts:
        counts[name] += 1
fig, ax = plt.subplots(figsize=(10, 5), dpi=150)
names = list(counts)
ax.barh(names, [counts[n] for n in names], color=[tuple(c / 255 for c in COLORS[n]) for n in names])
ax.invert_yaxis()
ax.set_xlabel("Labelled instances")
ax.set_title("%d images, %d labelled instances" % (len(images), sum(counts.values())))
for side in ("top", "right"):
    ax.spines[side].set_visible(False)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "03_class_stats.png"))
print("Images written to " + OUT)