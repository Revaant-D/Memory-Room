"""The one place that calls the reconstruction model.

    ########################################################################
    #  run_mapanything() BELOW HAS NEVER BEEN RUN.                         #
    #  It was written on a machine with no GPU and without the mapanything #
    #  package installed. It follows docs/reference/stage1.py, which has   #
    #  itself only run on synthetic rooms. Expect to fix it on first use.  #
    ########################################################################

Everything else in roompipe talks to the model through one small contract,
so the rest can be tested without it:

    a "model" is any function   run(list of image paths) -> ModelOutput

`roompipe.fake.FakeRoomModel` is such a function and is what the tests use.
"""

import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np

# Project rule: only the Apache-2.0 weights. Never "facebook/map-anything",
# which is the non-commercial release. The check in run_mapanything enforces it.
MODEL_ID = "facebook/map-anything-apache"


@dataclass
class ModelOutput:
    """What one pass of the model returns, in a frame of the model's own choosing."""

    points: np.ndarray  # N x 3, all views' points together
    colors: np.ndarray | None  # N x 3 whole numbers 0 to 255, or None if the model gave none
    poses: np.ndarray  # K x 4 x 4 camera-to-world, one per input image, in input order


_loaded = {}  # the model, kept between calls: loading it takes far longer than using it


def run_mapanything(image_paths, model_id=MODEL_ID, conf_drop_pct=20.0):
    """One MapAnything pass over the given images. NEVER RUN: see the top of this file.

    Things to check on the first real run, in the order they would bite:

    1. `load_images` is given a folder. The images are copied into a temporary
       folder under names 0000.jpg, 0001.jpg, ... on the assumption that it
       reads them in name order. If it does not, poses come back in the wrong
       order and every placement is wrong. Print the order once and compare.
    2. `load_images` forces every image to one shape (feasibility check, 2c).
       A portrait photo run with landscape frames loses much of its content.
    3. The colour key. The design says the model returns each input image as
       "img_no_norm". If the key is missing, colours come back as None and
       the room is drawn grey; the points and poses are unaffected.
    4. Whether 60 frames fit on a 16 GB GPU is undocumented.
    """
    if model_id != MODEL_ID:
        raise ValueError(f"only the Apache weights may be loaded ({MODEL_ID}), not {model_id!r}")

    import torch
    from mapanything.models import MapAnything
    from mapanything.utils.image import load_images

    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cpu":
        print("warning: no GPU found; this will be very slow", file=sys.stderr)
    if "model" not in _loaded:
        _loaded["model"] = MapAnything.from_pretrained(model_id).to(device)
    model = _loaded["model"]

    with tempfile.TemporaryDirectory() as folder:
        for i, path in enumerate(image_paths):
            shutil.copyfile(path, Path(folder) / f"{i:04d}{Path(path).suffix.lower()}")
        views = load_images(folder)
        preds = model.infer(
            views,
            memory_efficient_inference=True,
            use_amp=True,
            amp_dtype="bf16",  # falls back to fp16 on GPUs without bf16 (e.g. T4)
            apply_mask=True,
            mask_edges=True,
            apply_confidence_mask=False,
        )

    points, conf, colors, poses = [], [], [], []
    have_colors = True
    for pred in preds:
        mask = pred["mask"][0].cpu().numpy().reshape(-1).astype(bool)
        points.append(pred["pts3d"][0].float().cpu().numpy().reshape(-1, 3)[mask])
        conf.append(pred["conf"][0].float().cpu().numpy().reshape(-1)[mask])
        poses.append(pred["camera_poses"][0].float().cpu().numpy())
        if have_colors and "img_no_norm" in pred:
            colors.append(pred["img_no_norm"][0].float().cpu().numpy().reshape(-1, 3)[mask])
        else:
            have_colors = False

    points, conf = np.concatenate(points), np.concatenate(conf)
    keep = conf >= np.percentile(conf, conf_drop_pct)  # drop the least certain fifth
    rgb = None
    if have_colors:
        rgb = np.concatenate(colors)[keep]
        if rgb.max() <= 1.0:  # the image came as 0.0 to 1.0
            rgb = rgb * 255.0
        rgb = np.clip(np.rint(rgb), 0, 255).astype(np.uint8)
    return ModelOutput(points=points[keep], colors=rgb, poses=np.stack(poses))
