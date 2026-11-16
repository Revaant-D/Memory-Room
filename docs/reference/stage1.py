#!/usr/bin/env python3
"""Week-1 accuracy sprint, stage 1 (rescale-only arm).

Tests the fatal crux shared by I2-03 and I2-01 (see ../08-final-idea/NO-WINNER.md §2):
after scaling a phone-video reconstruction by ONE taped span, how far off are the
other wall-to-wall spans on the Galaxy S23 FE?

Two sub-commands:

  reconstruct  video -> keyframes -> MapAnything (Apache weights) -> wall planes.
               Writes rooms/<room>/recon.npz, walls.json, walls.png. Frames are
               deleted afterwards unless --keep-frames (privacy rule G5: no stored
               home imagery; only geometry is kept).

  evaluate     tape.csv + rooms/*/ -> per-span errors, per-room and pooled stats,
               the KILL/PASS call (kill if > 25% of held-out spans are off by
               > 3 cm after the tape), plus the Arm B (AR ruler) and Arm C
               (Orbit Measure) columns if you filled them in.

Typical flow per room:
  1. python stage1.py reconstruct --room r1 --video r1.mp4
  2. open rooms/r1/walls.png, find the wall IDs (W0, W1, ...) you taped between,
     and write them into tape.csv (wall_a, wall_b)
  3. after all rooms: python stage1.py evaluate --tape tape.csv

Only `evaluate` and the geometry code run without a GPU. `reconstruct` needs
torch + the map-anything package (see README.md in this folder).
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np

KILL_ERR_M = 0.03     # gate kill line: error above 3 cm ...
KILL_FRAC = 0.25      # ... on more than 25% of held-out spans
MODEL_ID = "facebook/map-anything-apache"  # Apache 2.0 weights (C-03). Never the NC ones.


# --------------------------------------------------------------------------- frames
def extract_frames(video: Path, out_dir: Path, n_frames: int = 60, max_side: int = 1024) -> int:
    """Split the video into n_frames equal time bins and keep the sharpest frame of each."""
    import cv2

    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise SystemExit(f"cannot open video {video}")
    if hasattr(cv2, "CAP_PROP_ORIENTATION_AUTO"):
        cap.set(cv2.CAP_PROP_ORIENTATION_AUTO, 1)  # apply phone rotation metadata -> upright frames
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
    if total <= 0:
        raise SystemExit("video reports 0 frames; re-encode it (e.g. ffmpeg -i in.mov out.mp4)")
    bin_size = max(1, total // n_frames)
    out_dir.mkdir(parents=True, exist_ok=True)
    best, best_score, idx, saved = None, -1.0, 0, 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        small = cv2.resize(frame, (320, int(320 * frame.shape[0] / frame.shape[1])))
        score = cv2.Laplacian(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var()
        if score > best_score:
            best, best_score = frame, score
        idx += 1
        if idx % bin_size == 0 and best is not None:
            h, w = best.shape[:2]
            s = max_side / max(h, w)
            if s < 1:
                best = cv2.resize(best, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
            cv2.imwrite(str(out_dir / f"f{saved:04d}.jpg"), best, [cv2.IMWRITE_JPEG_QUALITY, 95])
            saved += 1
            best, best_score = None, -1.0
            if saved >= n_frames:
                break
    cap.release()
    return saved


# ------------------------------------------------------------------ reconstruction
def run_mapanything(frame_dir: Path, model_id: str = MODEL_ID, conf_drop_pct: float = 20.0):
    """Returns (points Nx3, conf N, camera poses Kx4x4) in MapAnything's metric world frame."""
    import torch
    from mapanything.models import MapAnything
    from mapanything.utils.image import load_images

    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cpu":
        print("warning: no GPU found; this will be very slow", file=sys.stderr)
    model = MapAnything.from_pretrained(model_id).to(device)
    views = load_images(str(frame_dir))
    preds = model.infer(
        views,
        memory_efficient_inference=True,
        use_amp=True,
        amp_dtype="bf16",          # falls back to fp16 on GPUs without bf16 (e.g. T4)
        apply_mask=True,
        mask_edges=True,
        apply_confidence_mask=False,
    )
    pts, conf, poses = [], [], []
    for p in preds:
        P = p["pts3d"][0].float().cpu().numpy().reshape(-1, 3)
        C = p["conf"][0].float().cpu().numpy().reshape(-1)
        M = p["mask"][0].cpu().numpy().reshape(-1).astype(bool)
        pts.append(P[M])
        conf.append(C[M])
        poses.append(p["camera_poses"][0].float().cpu().numpy())
    pts, conf = np.concatenate(pts), np.concatenate(conf)
    keep = conf >= np.percentile(conf, conf_drop_pct)
    return pts[keep], conf[keep], np.stack(poses)


def voxel_downsample(pts: np.ndarray, voxel: float = 0.01, rng=None) -> np.ndarray:
    """Keep one random point per voxel. Returns indices into pts."""
    rng = rng or np.random.default_rng(0)
    order = rng.permutation(len(pts))
    keys = np.floor(pts[order] / voxel).astype(np.int64)
    _, first = np.unique(keys, axis=0, return_index=True)
    return order[first]


# ------------------------------------------------------------------------ geometry
def estimate_up(poses: np.ndarray) -> tuple[np.ndarray, float]:
    """World 'up' = minus the mean camera +Y (OpenCV: +Y points down in the image).

    Works because frames are upright (rotation metadata applied) and the phone is
    held roughly vertical. Returns (up, consistency); consistency near 1 is good,
    below ~0.8 means the camera tilted a lot and up is unreliable.
    """
    ydown = poses[:, :3, 1]
    m = ydown.mean(axis=0)
    strength = float(np.linalg.norm(m))
    return -m / strength, strength


def floor_height(pts: np.ndarray, up: np.ndarray, cam_pos: np.ndarray) -> float:
    """Height (along up) of the floor: the densest 1 cm height bin well below the cameras."""
    h = pts @ up
    below = h[h < np.median(cam_pos @ up) - 0.5]
    if len(below) < 100:
        raise ValueError("almost no points below the camera; did the video show the floor?")
    hist, edges = np.histogram(below, bins=np.arange(below.min(), below.max() + 0.01, 0.01))
    i = int(np.argmax(hist))
    return float((edges[i] + edges[i + 1]) / 2)


def _horizontal_basis(up: np.ndarray):
    a = np.array([1.0, 0, 0]) if abs(up[0]) < 0.9 else np.array([0, 1.0, 0])
    e1 = np.cross(up, a)
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(up, e1)
    return e1, e2


def fit_vertical_planes(pts, up, floor_h, dist=0.02, max_planes=12, min_pts=400,
                        min_extent=0.5, iters=3000, score_sample=20000, band=(0.15, 2.0), seed=0):
    """Sequential RANSAC for planes that contain the up vector (walls, furniture sides).

    A candidate plane through p_i, p_j is vertical by construction: normal =
    normalize((p_j - p_i) x up). Returns (planes, labels) where labels[k] is the
    plane index of point k or -1.
    """
    rng = np.random.default_rng(seed)
    h = pts @ up - floor_h
    in_band = np.where((h > band[0]) & (h < band[1]))[0]
    labels = -np.ones(len(pts), dtype=int)
    remaining = in_band.copy()
    e1, e2 = _horizontal_basis(up)
    planes = []
    for _ in range(max_planes):
        if len(remaining) < min_pts:
            break
        P = pts[remaining]
        S = P[rng.choice(len(P), size=min(score_sample, len(P)), replace=False)]
        best_n, best_c, best_score = None, None, -1
        for start in range(0, iters, 200):
            k = min(200, iters - start)
            i = rng.integers(0, len(P), size=k)
            j = rng.integers(0, len(P), size=k)
            n = np.cross(P[j] - P[i], up)
            nn = np.linalg.norm(n, axis=1)
            ok = nn > 0.05            # points at least ~5 cm apart horizontally
            if not ok.any():
                continue
            n = n[ok] / nn[ok, None]
            c = np.einsum("ij,ij->i", n, P[i[ok]])
            score = (np.abs(S @ n.T - c) < dist).sum(axis=0)
            b = int(np.argmax(score))
            if score[b] > best_score:
                best_n, best_c, best_score = n[b], c[b], int(score[b])
        if best_n is None:
            break
        inl = np.abs(P @ best_n - best_c) < dist
        # refine: 2D line fit (PCA) of the inliers' horizontal coordinates -> vertical plane
        for _ in range(2):
            Q = P[inl]
            xy = np.c_[Q @ e1, Q @ e2]
            mu = xy.mean(axis=0)
            _, _, vt = np.linalg.svd(xy - mu, full_matrices=False)
            n2 = vt[1]
            best_n = n2[0] * e1 + n2[1] * e2
            best_c = float(mu @ n2)
            inl = np.abs(P @ best_n - best_c) < dist
        Q = P[inl]
        along = np.cross(up, best_n)
        t = Q @ along
        extent = float(np.percentile(t, 98) - np.percentile(t, 2)) if len(t) else 0.0
        if inl.sum() >= min_pts and extent >= min_extent:
            pid = len(planes)
            labels[remaining[inl]] = pid
            resid = Q @ best_n - best_c
            planes.append({
                "id": f"W{pid}",
                "normal": best_n.tolist(),
                "offset": float(best_c),
                "inliers": int(inl.sum()),
                "rms_m": float(np.sqrt(np.mean(resid ** 2))),
                "extent_m": extent,
                "center": Q.mean(axis=0).tolist(),
            })
        remaining = remaining[~inl]
    return planes, labels


def span_between(planes, labels, pts, up, floor_h, wall_a, wall_b, height=1.0, band=0.15):
    """Distance between two (near-)parallel vertical planes, measured near `height` above the floor.

    Returns (distance_m, info). Uses inlier points of each wall within +/- band of
    the height (falls back to all inliers if fewer than 50 there) and averages the
    point-to-opposite-plane distances from both sides.
    """
    ids = {p["id"]: k for k, p in enumerate(planes)}
    for w in (wall_a, wall_b):
        if w not in ids:
            raise KeyError(f"wall {w} not found; available: {', '.join(ids)}")
    ka, kb = ids[wall_a], ids[wall_b]
    na, ca = np.array(planes[ka]["normal"]), planes[ka]["offset"]
    nb, cb = np.array(planes[kb]["normal"]), planes[kb]["offset"]
    angle = math.degrees(math.acos(min(1.0, abs(float(na @ nb)))))
    h = pts @ up - floor_h
    flags = []
    if angle > 5:
        flags.append(f"walls_not_parallel({angle:.1f}deg)")
    d = []
    for k, n_other, c_other in ((ka, nb, cb), (kb, na, ca)):
        sel = labels == k
        near = sel & (np.abs(h - height) < band)
        if near.sum() < 50:
            flags.append(f"{planes[k]['id']}_few_points_at_height")
            near = sel
        d.append(abs(float(np.mean(pts[near] @ n_other) - c_other)))
    return float(np.mean(d)), {"angle_deg": angle, "asym_m": abs(d[0] - d[1]), "flags": flags}


def plot_walls(path: Path, pts, labels, planes, up, cam_pos, title=""):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    e1, e2 = _horizontal_basis(up)
    fig, ax = plt.subplots(figsize=(8, 8))
    bg = labels < 0
    sub = np.where(bg)[0]
    if len(sub) > 30000:
        sub = np.random.default_rng(0).choice(sub, 30000, replace=False)
    ax.scatter(pts[sub] @ e1, pts[sub] @ e2, s=0.2, c="0.8")
    cmap = plt.get_cmap("tab20")
    for k, p in enumerate(planes):
        q = pts[labels == k]
        if len(q) > 8000:
            q = q[np.random.default_rng(k).choice(len(q), 8000, replace=False)]
        ax.scatter(q @ e1, q @ e2, s=0.5, color=cmap(k % 20))
        c = np.array(p["center"])
        ax.text(c @ e1, c @ e2, p["id"], fontsize=13, weight="bold",
                bbox=dict(facecolor="white", alpha=0.8, edgecolor=cmap(k % 20)))
    ax.plot(cam_pos @ e1, cam_pos @ e2, "k--", lw=0.8, label="camera path")
    ax.set_aspect("equal")
    ax.set_xlabel("m")
    ax.set_ylabel("m")
    ax.legend(loc="lower right")
    ax.set_title(title or "Top-down view: pick the wall IDs you taped between")
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def analyse_points(pts, poses, room_dir: Path, title=""):
    """Geometry part of `reconstruct` (no GPU). Writes recon.npz, walls.json, walls.png."""
    up, consistency = estimate_up(poses)
    cam_pos = poses[:, :3, 3]
    fh = floor_height(pts, up, cam_pos)
    planes, labels = fit_vertical_planes(pts, up, fh)
    room_dir.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(room_dir / "recon.npz", points=pts.astype(np.float32), labels=labels,
                        poses=poses.astype(np.float32), up=up, floor_h=fh)
    meta = {"up": up.tolist(), "up_consistency": consistency, "floor_h": fh,
            "n_points": int(len(pts)), "walls": planes}
    (room_dir / "walls.json").write_text(json.dumps(meta, indent=2))
    plot_walls(room_dir / "walls.png", pts, labels, planes, up, cam_pos, title)
    if consistency < 0.8:
        print(f"warning: up-direction consistency {consistency:.2f} < 0.8; check walls.png",
              file=sys.stderr)
    return meta


# ------------------------------------------------------------------------ evaluate
def _f(row, key):
    v = (row.get(key) or "").strip()
    return float(v) if v else None


def binom_upper(k: int, n: int, conf: float = 0.8) -> float:
    """One-sided Clopper-Pearson upper bound on a proportion (k successes of n)."""
    if n == 0:
        return 1.0
    if k >= n:
        return 1.0
    alpha = 1 - conf
    cdf = lambda p: sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k + 1))
    lo, hi = k / n, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if cdf(mid) > alpha else (lo, mid)
    return hi


def _pair(r):
    a, b = (r.get("wall_a") or "").strip(), (r.get("wall_b") or "").strip()
    return "|".join(sorted((a, b))) if a and b else ""


def evaluate(tape_csv: Path, rooms_dir: Path, out_dir: Path, tolerance_cm: float = 2.0):
    rows = list(csv.DictReader(open(tape_csv, newline="")))
    if not rows:
        raise SystemExit("tape.csv is empty")
    by_room: dict[str, list] = {}
    for r in rows:
        by_room.setdefault(r["room_id"].strip(), []).append(r)

    results, room_stats, tape_diffs = [], [], []
    for room, rs in by_room.items():
        rdir = rooms_dir / room
        recon = None
        if (rdir / "recon.npz").exists():
            z = np.load(rdir / "recon.npz")
            meta = json.loads((rdir / "walls.json").read_text())
            recon = (z["points"].astype(np.float64), z["labels"], z["up"], float(z["floor_h"]),
                     meta["walls"])
        for r in rs:
            t1, t2 = _f(r, "tape1_m"), _f(r, "tape2_m")
            if t1 is None:
                raise SystemExit(f"{room}/{r['span_id']}: tape1_m is required")
            if t2 is not None:
                tape_diffs.append(t1 - t2)
            r["_tape"] = t1 if t2 is None else (t1 + t2) / 2
            r["_model"], r["_info"] = None, {}
            if recon and r.get("wall_a", "").strip() and r.get("wall_b", "").strip():
                pts, labels, up, fh, planes = recon
                r["_model"], r["_info"] = span_between(
                    planes, labels, pts, up, fh, r["wall_a"].strip(), r["wall_b"].strip(),
                    height=_f(r, "height_m") or 1.0)
        # Arm A: rescale by one taped span (is_scale=1, else the longest taped span)
        armA = [r for r in rs if r["_model"] is not None]
        scale_row, s = None, None
        if armA:
            marked = [r for r in armA if (r.get("is_scale") or "").strip() == "1"]
            scale_row = marked[0] if marked else max(armA, key=lambda r: r["_tape"])
            s = scale_row["_tape"] / scale_row["_model"]
        errs = []
        scale_pair = _pair(scale_row) if scale_row else None
        for r in rs:
            out = {"room_id": room, "span_id": r["span_id"], "room_type": r.get("room_type", ""),
                   "pair": _pair(r),
                   "tape_m": round(r["_tape"], 4), "role": "", "model_raw_m": "", "pred_m": "",
                   "err_m": "", "raw_err_m": "", "arruler_err_m": "", "orbit_err_m": "",
                   "flags": ";".join(r["_info"].get("flags", []))}
            if r["_model"] is not None:
                out["model_raw_m"] = round(r["_model"], 4)
                out["raw_err_m"] = round(r["_model"] - r["_tape"], 4)
                if r is scale_row:
                    out["role"] = "scale"
                elif _pair(r) == scale_pair:
                    # same two walls as the taped span (another height): the tape already fixed this
                    # pair, so it barely tests anything. Reported, but excluded from the kill rule.
                    pred = s * r["_model"]
                    out.update(role="scale_pair", pred_m=round(pred, 4), err_m=round(pred - r["_tape"], 4))
                else:
                    pred = s * r["_model"]
                    out.update(role="held_out", pred_m=round(pred, 4), err_m=round(pred - r["_tape"], 4))
                    errs.append(pred - r["_tape"])
            ar, orb = _f(r, "arruler_m"), _f(r, "orbit_m")
            if ar is not None:
                out["arruler_err_m"] = round(ar - r["_tape"], 4)
            if orb is not None:
                out["orbit_err_m"] = round(orb - r["_tape"], 4)
            results.append(out)
        e = np.abs(np.array(errs))
        room_stats.append({
            "room_id": room, "room_type": rs[0].get("room_type", ""),
            "n_held_out": int(len(e)),
            "scale_span": scale_row["span_id"] if scale_row else None,
            "scale_factor": round(s, 4) if s else None,
            "frac_over_3cm": round(float((e > KILL_ERR_M).mean()), 3) if len(e) else None,
            "median_abs_err_cm": round(float(np.median(e)) * 100, 2) if len(e) else None,
            "max_abs_err_cm": round(float(e.max()) * 100, 2) if len(e) else None,
            "has_reconstruction": recon is not None,
        })

    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "results.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        w.writeheader()
        w.writerows(results)

    summary = {"rooms": room_stats}
    held = np.abs([r["err_m"] for r in results if r["role"] == "held_out"])
    if len(held):
        frac = float((held > KILL_ERR_M).mean())
        # independent view: one value per (room, wall pair) = the WORST height variant of that pair
        worst: dict = {}
        for r in results:
            if r["role"] == "held_out":
                key = (r["room_id"], r["pair"] or r["span_id"])
                worst[key] = max(worst.get(key, 0.0), abs(r["err_m"]))
        ind = np.array(list(worst.values()))
        k_over = int((ind > KILL_ERR_M).sum())
        frac_ind = k_over / len(ind)
        upper = binom_upper(k_over, len(ind), 0.8)
        verdict = "KILL" if (frac > KILL_FRAC or frac_ind > KILL_FRAC) else "PASS"
        summary["armA_rescale_only"] = {
            "n_held_out": int(len(held)), "n_rooms": sum(1 for r in room_stats if r["n_held_out"]),
            "frac_over_3cm": round(frac, 3),
            "median_abs_err_cm": round(float(np.median(held)) * 100, 2),
            "p90_abs_err_cm": round(float(np.percentile(held, 90)) * 100, 2),
            "independent_pairs": {
                "n": int(len(ind)),
                "frac_over_3cm": round(frac_ind, 3),
                "upper80_frac_over_3cm": round(upper, 3),
                "note": "one value per (room, wall pair): the worst of its height variants. "
                        "This is the honest sample size; variants of the taped pair are excluded.",
            },
            "verdict": verdict,
            "verdict_confidence": ("tentative: fewer than 10 independent pairs" if len(ind) < 10 else
                                   "firm" if upper <= KILL_FRAC or frac_ind > KILL_FRAC else
                                   "borderline: the 80% upper bound exceeds the kill line; add rooms"),
            "rooms_failing": [r["room_id"] for r in room_stats
                              if r["frac_over_3cm"] is not None and r["frac_over_3cm"] > KILL_FRAC],
        }
        white = np.abs([r["err_m"] for r in results
                        if r["role"] == "held_out" and "white" in r["room_type"].lower()])
        if len(white):
            summary["armA_rescale_only"]["white_wall_frac_over_3cm"] = round(float((white > KILL_ERR_M).mean()), 3)
    if tape_diffs:
        summary["tape_sigma_cm"] = round(float(np.std(tape_diffs, ddof=1) / math.sqrt(2)) * 100, 2) \
            if len(tape_diffs) > 1 else None

    # Arm B: AR ruler proxy -> per-phone bias and residual scale spread
    ar_rows = [(float(r["arruler_err_m"]) + r["tape_m"], r["tape_m"]) for r in results if r["arruler_err_m"] != ""]
    if len(ar_rows) >= 3:
        ratio = np.array([a / t for a, t in ar_rows])
        bias = float(np.median(ratio))
        spread = float(np.std(ratio / bias - 1, ddof=1))
        tol = tolerance_cm / 100
        summary["armB_ar_ruler_proxy"] = {
            "n": len(ratio), "bias_pct": round((bias - 1) * 100, 2),
            "scale_spread_pct": round(spread * 100, 2),
            "tolerance_cm": tolerance_cm,
            "green_at_tolerance_k1": spread <= tol / 4.0,
            f"green_possible_at_{tolerance_cm:g}cm_on_4m_k1": spread <= tol / 4.0,
            f"green_possible_at_{tolerance_cm:g}cm_on_4m_k2": spread <= tol / 8.0,
            "green_possible_at_5cm_on_4m_k1": spread <= 0.05 / 4.0,
            "note": "proxy for raw ARCore span error only; it cannot confirm I2-01's pipeline",
        }
    # Arm C: Orbit Measure baseline
    oe = np.abs([float(r["orbit_err_m"]) for r in results if r["orbit_err_m"] != ""])
    if len(oe):
        summary["armC_orbit_measure"] = {
            "n": int(len(oe)), "median_abs_err_cm": round(float(np.median(oe)) * 100, 2),
            "frac_over_3cm": round(float((oe > KILL_ERR_M).mean()), 3),
            "frac_within_half_inch": round(float((oe <= 0.0127).mean()), 3),
        }
    summary["route"] = route(summary)
    summary["h3_paste"] = h3_block(summary)
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    return summary


def h3_block(s: dict) -> str:
    """Lines to paste under H3 in creating-idea/00-brief/human-notes.md (first-hand evidence)."""
    L = ["Sprint stage 1 (first-hand, builder's S23 FE):"]
    A = s.get("armA_rescale_only")
    if A:
        I = A["independent_pairs"]
        L.append(f"- Arm A (I2-03, video + one tape): {A['verdict']} ({A['verdict_confidence']}). "
                 f"{A['n_rooms']} rooms, {A['n_held_out']} held-out spans: {A['frac_over_3cm']:.0%} over 3 cm, "
                 f"median {A['median_abs_err_cm']} cm, p90 {A['p90_abs_err_cm']} cm. Independent wall pairs: "
                 f"{I['n']}, {I['frac_over_3cm']:.0%} over 3 cm (80% upper bound {I['upper80_frac_over_3cm']:.0%}).")
        if "white_wall_frac_over_3cm" in A:
            L.append(f"- White-walled rooms: {A['white_wall_frac_over_3cm']:.0%} of spans over 3 cm.")
        L.append("- Per room: " + "; ".join(
            f"{r['room_id']} {r['median_abs_err_cm']} cm median, {r['frac_over_3cm']:.0%} >3 cm"
            for r in s["rooms"] if r["n_held_out"]))
    if s.get("tape_sigma_cm") is not None:
        L.append(f"- Tape repeatability sigma: {s['tape_sigma_cm']} cm.")
    B = s.get("armB_ar_ruler_proxy")
    if B:
        L.append(f"- Arm B proxy (I2-01, AR ruler): bias {B['bias_pct']}%, scale spread {B['scale_spread_pct']}% "
                 f"(n={B['n']}); green possible at {B['tolerance_cm']:g} cm: {B['green_at_tolerance_k1']}; "
                 f"at 5 cm: {B['green_possible_at_5cm_on_4m_k1']}.")
    C = s.get("armC_orbit_measure")
    if C:
        L.append(f"- Arm C (Orbit Measure): median {C['median_abs_err_cm']} cm, {C['frac_over_3cm']:.0%} over 3 cm, "
                 f"{C['frac_within_half_inch']:.0%} within half an inch (n={C['n']}).")
    L.append(f"- Route: {s['route']}")
    return "\n".join(L)


def route(summary: dict) -> str:
    """The NO-WINNER §2 decision table."""
    a = summary.get("armA_rescale_only", {}).get("verdict")
    b = summary.get("armB_ar_ruler_proxy")
    if a is None:
        return "No held-out spans with a reconstruction yet: run `reconstruct` and fill wall_a/wall_b."
    b_ok = None if b is None else b["green_at_tolerance_k1"]
    if a == "PASS" and b_ok in (True, None):
        return "Arm A passes: build I2-03 first." + (" Arm B also small: later fold I2-01's cause tags in."
                                                   if b_ok else " (Arm B not measured.)")
    if a == "PASS":
        return "Arm A passes, Arm B spread too large: build I2-03, park I2-01."
    if b_ok:
        return "Arm A fails, Arm B small: move to I2-01 and run its full 2-week replay."
    if b is not None and b.get("green_possible_at_5cm_on_4m_k1"):
        return "Arm A fails and Arm B fails at your tolerance but passes at +/-5 cm: consider quote-grade I2-01."
    return ("Both arms fail (or Arm B not measured): the scan-accuracy line looks dead on this phone at "
            "survey grade. Re-check at +/-5 cm, then fall back to I-01b (NO-WINNER §5).")


# ----------------------------------------------------------------------------- CLI
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("reconstruct", help="video -> walls.png/walls.json/recon.npz (needs GPU)")
    r.add_argument("--room", required=True)
    r.add_argument("--video", required=True, type=Path)
    r.add_argument("--rooms-dir", type=Path, default=Path("rooms"))
    r.add_argument("--frames", type=int, default=60, help="keyframes to use (lower if GPU memory runs out)")
    r.add_argument("--conf-drop-pct", type=float, default=20.0, help="drop this lowest-confidence percent")
    r.add_argument("--voxel", type=float, default=0.01)
    r.add_argument("--keep-frames", action="store_true", help="keep extracted JPGs (off by default: G5)")
    e = sub.add_parser("evaluate", help="tape.csv -> results.csv/summary.json + KILL/PASS")
    e.add_argument("--tape", required=True, type=Path)
    e.add_argument("--rooms-dir", type=Path, default=Path("rooms"))
    e.add_argument("--out", type=Path, default=Path("out"))
    e.add_argument("--tolerance-cm", type=float, default=2.0)
    a = ap.parse_args(argv)

    if a.cmd == "reconstruct":
        room_dir = a.rooms_dir / a.room
        tmp = Path(tempfile.mkdtemp(prefix=f"frames_{a.room}_"))
        try:
            n = extract_frames(a.video, tmp, a.frames)
            print(f"{n} keyframes extracted")
            pts, conf, poses = run_mapanything(tmp, conf_drop_pct=a.conf_drop_pct)
            keep = voxel_downsample(pts, a.voxel)
            meta = analyse_points(pts[keep], poses, room_dir, title=f"{a.room}: pick the walls you taped")
        finally:
            if a.keep_frames:
                print(f"frames kept in {tmp}")
            else:
                shutil.rmtree(tmp, ignore_errors=True)
        print(f"{len(meta['walls'])} vertical planes; up consistency {meta['up_consistency']:.2f}")
        for w in meta["walls"]:
            print(f"  {w['id']}: {w['inliers']} pts, extent {w['extent_m']:.2f} m, rms {w['rms_m']*100:.1f} cm")
        print(f"now open {room_dir/'walls.png'} and fill wall_a/wall_b in tape.csv")
    else:
        s = evaluate(a.tape, a.rooms_dir, a.out, a.tolerance_cm)
        print(json.dumps({k: v for k, v in s.items() if k != "h3_paste"}, indent=2))
        print("\n--- paste under H3 in creating-idea/00-brief/human-notes.md ---")
        print(s["h3_paste"])


if __name__ == "__main__":
    main()
