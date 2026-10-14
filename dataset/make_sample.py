import json
import os
import random
import shutil

SRC = r"C:\Users\june\Documents\SIT_dataset\output"
DST = r"C:\Users\june\Documents\pantograph-synthetic-data\sample_data"
N = 20

coco = json.load(open(os.path.join(SRC, "coco_data", "coco_annotations.json")))
random.seed(1)
imgs = random.sample(coco["images"], N)
ids = {i["id"] for i in imgs}

sample = {k: v for k, v in coco.items() if k not in ("images", "annotations")}
sample["images"] = imgs
sample["annotations"] = [a for a in coco["annotations"] if a["image_id"] in ids]

os.makedirs(os.path.join(DST, "images"), exist_ok=True)
for i in imgs:
    shutil.copy(os.path.join(SRC, "coco_data", i["file_name"]), os.path.join(DST, i["file_name"]))
json.dump(sample, open(os.path.join(DST, "coco_annotations.json"), "w"))

names = {i["file_name"] for i in imgs}
with open(os.path.join(SRC, "wear_labels.jsonl")) as f, \
     open(os.path.join(DST, "wear_labels.jsonl"), "w") as g:
    for line in f:
        if json.loads(line)["image"] in names:
            g.write(line)
print("Sample written: %d images, %d annotations" % (N, len(sample["annotations"])))