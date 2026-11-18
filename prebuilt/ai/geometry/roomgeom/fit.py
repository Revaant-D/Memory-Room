"""Lining one set of 3D points up with another.

Every run of the reconstruction model invents its own frame: its own origin,
its own rotation, and a slightly different scale. To use a new run's answer
inside a stored room, the new frame has to be moved onto the room's frame.

The way to find that move: pick things whose position is known in BOTH frames
(the "anchor" frames kept from the room video; their camera centres), and
find the scale s, rotation R and shift t that carry the new positions onto
the stored ones as closely as possible. That is the Umeyama fit.

Source of the method: docs/reference (T5 technical design, "Placing a photo,
and knowing when not to"). The fit below follows that sketch; the input
checks and `spread` are additions.
"""

import numpy as np


def umeyama(src, dst):
    """Return (s, R, t) so that  dst ≈ s * R @ src + t  for matching rows.

    src, dst: N x 3 arrays, row i of each being the same thing seen in the
    two frames. N must be at least 3 and the points must not all lie on one
    line (see `spread`).

    s is a positive number, R a 3 x 3 rotation (never a mirror image), t a
    length-3 shift.
    """
    src = np.asarray(src, dtype=float)
    dst = np.asarray(dst, dtype=float)
    if src.shape != dst.shape or src.ndim != 2 or src.shape[1] != 3:
        raise ValueError("src and dst must both be N x 3")
    if len(src) < 3:
        raise ValueError("a fit needs at least 3 matching points")
    if not (np.isfinite(src).all() and np.isfinite(dst).all()):
        raise ValueError("the points to fit contain values that are not real numbers")

    mu_s, mu_d = src.mean(0), dst.mean(0)
    X, Y = src - mu_s, dst - mu_d
    variance = (X**2).sum() / len(src)
    if variance < 1e-18:
        raise ValueError("the source points are all in one spot; nothing to fit")

    U, D, Vt = np.linalg.svd(Y.T @ X / len(src))
    S = np.eye(3)
    # Without this, the best "rotation" can be a mirror image when the points
    # are flat (cameras all at one height). A room is never its own mirror.
    if np.linalg.det(U) * np.linalg.det(Vt) < 0:
        S[2, 2] = -1.0
    R = U @ S @ Vt
    s = float(np.trace(np.diag(D) @ S) / variance)
    t = mu_d - s * R @ mu_s
    return s, R, t


def apply_fit(s, R, t, points):
    """Move N x 3 points (or one length-3 point) with a fit from `umeyama`."""
    points = np.asarray(points, dtype=float)
    return s * points @ R.T + t


def fit_residuals(s, R, t, src, dst):
    """How far each source point lands from its partner after the fit, in dst's units."""
    return np.linalg.norm(apply_fit(s, R, t, src) - np.asarray(dst, dtype=float), axis=1)


def spread(points):
    """How spread out a set of points is, along its three main directions.

    Returns three numbers, largest first, in the points' own units: roughly
    the typical distance from the middle along the longest direction, the
    next, and the flattest.

    Why it matters: a fit needs the anchors spread in at least two
    directions. Cameras that walked around a room at one height are flat
    (third number near 0), which is fine. Cameras that stood almost in a
    line (second number near 0 too) leave the fit free to spin around that
    line, and every placement made with it is a guess.
    """
    points = np.asarray(points, dtype=float)
    centred = points - points.mean(0)
    return np.linalg.svd(centred, compute_uv=False) / np.sqrt(len(points))


def on_a_line(points, least_second_spread=0.05):
    """True when the points are too close to one line to fit a rotation from.

    `least_second_spread` is in the points' units (metres for a room): the
    anchors must be spread at least this much in a second direction. 5 cm is
    a starting guess, not a measured number.
    """
    return bool(spread(points)[1] < least_second_spread)
