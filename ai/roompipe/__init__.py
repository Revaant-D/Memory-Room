"""roompipe: the steps around the reconstruction model.

    roompipe.frames   pick sharp frames from a room video              (needs opencv)
    roompipe.model    the one function that calls MapAnything          (needs a GPU; NEVER RUN ON ONE)
    roompipe.build    frames -> model -> levelled room folder on disk
    roompipe.place    room folder + photos -> model -> pin or ask, per photo
    roompipe.session  helpers for the Colab notebook (ai/build_room_colab.ipynb)
    roompipe.fake     a stand-in for the model, for tests and dry runs

Everything except roompipe.model is tested with the stand-in model. See
ai/README.md.

roompipe uses roomgeom, which sits beside it in ai/. If roomgeom is not
already importable, that folder is added to the path here.
"""

import sys
from pathlib import Path

try:
    import roomgeom  # noqa: F401
except ImportError:
    _beside = Path(__file__).resolve().parents[1]
    if (_beside / "roomgeom").is_dir():
        sys.path.insert(0, str(_beside))
