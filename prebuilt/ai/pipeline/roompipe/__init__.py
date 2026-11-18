"""roompipe: the steps around the reconstruction model.

    roompipe.frames   pick sharp frames from a room video              (needs opencv)
    roompipe.model    the one function that calls MapAnything          (needs a GPU; NEVER RUN)
    roompipe.build    frames -> model -> levelled room folder on disk
    roompipe.place    room folder + photos -> model -> pin or ask, per photo
    roompipe.fake     a stand-in for the model, for tests and for a demo room

Everything except roompipe.model is tested with the stand-in model. See
README.md in the folder above.

roompipe uses roomgeom (prebuilt/ai/geometry). If roomgeom is not already
importable, the sibling folder is added to the path here, so the two work
straight from this repository. In Colab, upload both folders side by side.
"""

import sys
from pathlib import Path

try:
    import roomgeom  # noqa: F401
except ImportError:
    _sibling = Path(__file__).resolve().parents[2] / "geometry"
    if (_sibling / "roomgeom").is_dir():
        sys.path.insert(0, str(_sibling))
