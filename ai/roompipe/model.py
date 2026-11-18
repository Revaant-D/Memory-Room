"""The one place that calls the reconstruction model.

    ########################################################################
    #  run_mapanything() BELOW HAS NEVER BEEN RUN ON A GPU.                #
    #  It was checked line by line against the MapAnything source at      #
    #  commit 3d10cf7 (README, mapanything/utils/image.py and the infer() #
    #  signature in mapanything/models/mapanything/model.py) on 17 Nov    #
    #  2026, but nothing has executed it. Expect to fix it on first use.  #
    ########################################################################

Everything else in roompipe talks to the model through one small contract,
so the rest can be tested without it:

    a "model" is any function   run(list of image paths) -> ModelOutput

`roompipe.fake.FakeRoomModel` is such a function and is what the tests use.
"""

import sys
from dataclasses import dataclass

import numpy as np

# Project rule: only the Apache-2.0 weights. Never "facebook/map-anything",
# which is the non-commercial release. The check in load_model enforces it.
MODEL_ID = "facebook/map-anything-apache"

# What the first real run is pinned to, so its result can be reproduced.
# Looked up on 17 Nov 2026: the weights' latest revision on Hugging Face
# (last changed 4 Feb 2026) and the newest commit of the code on GitHub.
WEIGHTS_REVISION = "00f9c245bbcb60522d1ed7f9e9d88462c6e3f38a"
CODE_COMMIT = "3d10cf7a3016fc0f9bb13a071ee66c47b10be0d9"

IMAGE_ENDINGS = (".jpg", ".jpeg", ".png")  # what mapanything's load_images reads without extras

PRECISIONS = ("auto", "bf16", "fp16", "fp32")
MOST_INVALID = 0.01  # more than 1% of points not real numbers: the pass is not trusted


def amp_dtype_for(capability_major):
    """The number format for the model's pass on a GPU of this generation.

    bf16 needs an Ampere-or-newer GPU (compute capability 8 or more). Older
    ones, such as Colab's free T4 (7.5), get fp16; this is the rule Meta's
    VGGT uses. It is decided here and not left to MapAnything, whose check
    (torch.cuda.is_bf16_supported) can answer True on a T4, where bf16 is only
    emulated. Checked in MapAnything's mapanything/utils/device.py at the
    pinned commit, 17 Nov 2026.
    """
    return "bf16" if capability_major >= 8 else "fp16"


def invalid_output_problem(poses, n_points, n_invalid, precision):
    """A sentence saying why a pass's output cannot be used, or None if it can.

    fp16 can overflow inside a large model and hand back NaN; fp32 avoids it
    at the cost of memory, so the sentence says how to switch.
    """
    hint = "" if precision == "fp32" else " Set PRECISION = \"fp32\" in the notebook's settings and run again."
    if not np.isfinite(np.asarray(poses, dtype=float)).all():
        return f"the model returned camera positions that are not real numbers (precision {precision}).{hint}"
    if n_points == 0:
        return "the model kept no points at all; the frames may be too dark or too blurred"
    if n_invalid > MOST_INVALID * n_points:
        return (f"{n_invalid:,} of {n_points:,} points from the model are not real numbers "
                f"(precision {precision}).{hint}")
    return None


@dataclass
class ModelOutput:
    """What one pass of the model returns, in a frame of the model's own choosing."""

    points: np.ndarray  # N x 3, all views' points together, least certain ones dropped
    colors: np.ndarray | None  # N x 3 whole numbers 0 to 255, or None if the model gave none
    poses: np.ndarray  # K x 4 x 4 camera-to-world, one per input image, in input order
    # Optional, filled only when asked for (keep_views=True): one dict per input image, with
    #   image      H x W x 3 uint8   the picture exactly as the model saw it (resized and cropped)
    #   points     H x W x 3 float   the 3D point behind every pixel, in the model's frame
    #   conf       H x W float       the model's confidence per pixel (higher is surer)
    #   mask       H x W bool        pixels the model considers valid
    #   intrinsics 3 x 3             the camera the model inferred, for that H x W picture
    views: list | None = None
    info: dict | None = None  # facts about the pass, e.g. the confidence cut-off used


_loaded = {}  # the model, kept between calls: loading it takes far longer than using it


def load_model(model_id=MODEL_ID, revision=WEIGHTS_REVISION):
    """Load MapAnything once and keep it. Refuses any weights but the Apache ones."""
    if model_id != MODEL_ID:
        raise ValueError(f"only the Apache weights may be loaded ({MODEL_ID}), not {model_id!r}")
    key = (model_id, revision)
    if _loaded.get("key") != key:
        import torch
        from mapanything.models import MapAnything

        device = "cuda" if torch.cuda.is_available() else "cpu"
        if device == "cpu":
            print("warning: no GPU found; this will be very slow", file=sys.stderr)
        _loaded.clear()
        # MapAnything is a huggingface_hub PyTorchModelHubMixin, so from_pretrained takes `revision`.
        _loaded["model"] = MapAnything.from_pretrained(model_id, revision=revision).to(device)
        _loaded["model"].eval()
        _loaded["key"] = key
    return _loaded["model"]


def _numpy(tensor):
    return tensor.detach().float().cpu().numpy()


def run_mapanything(image_paths, model_id=MODEL_ID, revision=WEIGHTS_REVISION, conf_drop_pct=20.0,
                    keep_views=False, precision="auto"):
    """One MapAnything pass over the given images. NEVER RUN ON A GPU: see the top of this file.

    The images go to `load_images` as a list, in the order given; it reads them
    in that order (checked in its source). It silently skips anything it cannot
    read, which would shift every pose after it, so the count is checked.

    precision: "auto" (bf16 on newer GPUs, fp16 on a T4; see amp_dtype_for),
    or "bf16", "fp16", "fp32". fp32 is the safe choice if fp16 returns NaN,
    and uses about twice the memory.

    Things to check on the first real run, in the order they would bite:

    1. `load_images` forces every image to one shape, chosen from the average
       aspect ratio of the set (feasibility check, 2c). Portrait photos run
       with landscape frames lose much of their content.
    2. Whether 60 frames fit on a 16 GB GPU is undocumented. The notebook
       retries with fewer frames when memory runs out.
    3. `img_no_norm` is documented as the de-normalised input picture. If it
       comes back in 0 to 255 rather than 0 to 1, the conversion below copes.
    """
    if model_id != MODEL_ID:  # before anything is imported or downloaded
        raise ValueError(f"only the Apache weights may be loaded ({MODEL_ID}), not {model_id!r}")
    if precision not in PRECISIONS:
        raise ValueError(f"precision must be one of {PRECISIONS}, not {precision!r}")
    paths = [str(p) for p in image_paths]
    unreadable = [p for p in paths if not p.lower().endswith(IMAGE_ENDINGS)]
    if unreadable:
        raise ValueError(f"the model reads only {', '.join(IMAGE_ENDINGS)} files; convert {unreadable[:3]}")
    import torch
    from mapanything.utils.image import load_images

    model = load_model(model_id, revision)
    loaded = load_images(paths)
    if len(loaded) != len(paths):
        raise ValueError(f"the image loader read {len(loaded)} of {len(paths)} images; one is unreadable")

    if precision == "auto":
        on_gpu = torch.cuda.is_available()
        precision = amp_dtype_for(torch.cuda.get_device_capability()[0]) if on_gpu else "fp32"
    with torch.no_grad():
        preds = model.infer(
            loaded,
            memory_efficient_inference=True,
            use_amp=precision != "fp32",
            amp_dtype=precision,  # chosen above; MapAnything's own bf16 check can say yes on a T4
            apply_mask=True,
            mask_edges=True,
            apply_confidence_mask=False,
        )

    points, conf, colors, poses, views = [], [], [], [], []
    have_colors = True
    for pred in preds:
        pts = _numpy(pred["pts3d"][0])  # H x W x 3
        height, width = pts.shape[:2]
        mask = _numpy(pred["mask"][0]).reshape(height, width) > 0.5
        c = _numpy(pred["conf"][0]).reshape(height, width)
        poses.append(_numpy(pred["camera_poses"][0]))
        points.append(pts[mask])
        conf.append(c[mask])
        image = None
        if "img_no_norm" in pred:
            image = _numpy(pred["img_no_norm"][0]).reshape(height, width, 3)
            if image.max() <= 1.0 + 1e-6:  # the picture came as 0.0 to 1.0
                image = image * 255.0
            image = np.clip(np.rint(image), 0, 255).astype(np.uint8)
            colors.append(image[mask])
        else:
            have_colors = False
        if keep_views:
            views.append({
                "image": image if image is not None else np.zeros((height, width, 3), np.uint8),
                "points": pts,
                "conf": c,
                "mask": mask,
                "intrinsics": _numpy(pred["intrinsics"][0]) if "intrinsics" in pred else None,
            })
    del preds
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    points, conf = np.concatenate(points), np.concatenate(conf)
    rgb = np.concatenate(colors) if have_colors else None
    poses = np.stack(poses)
    finite = np.isfinite(points).all(axis=1) & np.isfinite(conf)
    n_invalid = int((~finite).sum())
    problem = invalid_output_problem(poses, len(points), n_invalid, precision)
    if problem:
        raise ValueError(problem)
    points, conf = points[finite], conf[finite]
    rgb = rgb[finite] if rgb is not None else None

    threshold = float(np.percentile(conf, conf_drop_pct))
    keep = conf >= threshold  # drop the least certain fifth
    info = {
        "model_id": model_id,
        "weights_revision": revision,
        "precision": precision,
        "images": len(paths),
        "model_image_size": [int(width), int(height)],  # width x height the model worked at
        "conf_drop_pct": conf_drop_pct,
        "conf_threshold": threshold,
        "points_before_drop": int(len(points)),
        "invalid_points_dropped": n_invalid,
        "has_colors": have_colors,
    }
    return ModelOutput(points=points[keep], colors=rgb[keep] if rgb is not None else None, poses=poses,
                       views=views if keep_views else None, info=info)
