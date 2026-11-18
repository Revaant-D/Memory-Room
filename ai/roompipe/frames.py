"""Picking frames from a room video.

A phone films 30 frames a second; the model wants about 60 in all. The video
is cut into that many equal stretches of time and the sharpest frame of each
stretch is kept, so a blurred moment while the phone was moving does not
become one of the 60.

Adapted from extract_frames in docs/reference/stage1.py. Needs opencv
(`pip install opencv-python-headless`).
"""

from pathlib import Path


def extract_frames(video, out_dir, n_frames=60, max_side=1024):
    """Write up to `n_frames` sharp, upright frames as JPEGs. Returns their paths, in time order.

    max_side: frames larger than this on their long side are shrunk to it.
    Raises ValueError if the video cannot be read.
    """
    import cv2

    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise ValueError(f"cannot open video {video}")
    if hasattr(cv2, "CAP_PROP_ORIENTATION_AUTO"):
        # Phones store a sideways picture plus a note saying which way is up.
        cap.set(cv2.CAP_PROP_ORIENTATION_AUTO, 1)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
    if total <= 0:
        cap.release()
        raise ValueError("the video reports 0 frames; re-encode it (ffmpeg -i in.mov out.mp4)")

    stretch = max(1, total // n_frames)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    best, best_score, seen = None, -1.0, 0
    while len(paths) < n_frames:
        ok, frame = cap.read()
        if not ok:
            break
        # Sharpness: how much a small grey copy changes from pixel to pixel.
        small = cv2.resize(frame, (320, max(1, int(320 * frame.shape[0] / frame.shape[1]))))
        score = cv2.Laplacian(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var()
        if score > best_score:
            best, best_score = frame, score
        seen += 1
        if seen % stretch == 0 and best is not None:
            height, width = best.shape[:2]
            shrink = max_side / max(height, width)
            if shrink < 1:
                best = cv2.resize(
                    best, (int(width * shrink), int(height * shrink)), interpolation=cv2.INTER_AREA
                )
            path = out_dir / f"f{len(paths):04d}.jpg"
            cv2.imwrite(str(path), best, [cv2.IMWRITE_JPEG_QUALITY, 95])
            paths.append(path)
            best, best_score = None, -1.0
    cap.release()
    return paths
