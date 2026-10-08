"""Real OpenCV models: runs only when they are downloaded (CI downloads them)."""

import os

import numpy as np
import pytest

from attendance.config import Config
from attendance.face import FaceEngine, FaceError, decode_image

engine = FaceEngine(os.getenv("MODELS_DIR", Config.MODELS_DIR))
pytestmark = pytest.mark.skipif(not engine.available, reason="face models not downloaded")


def test_blank_image_has_no_faces():
    assert engine.analyze(np.full((480, 640, 3), 127, np.uint8)) == []
    with pytest.raises(FaceError):
        engine.single_face(np.full((480, 640, 3), 127, np.uint8))


def test_decode_rejects_garbage():
    with pytest.raises(FaceError):
        decode_image("data:image/png;base64,bm90IGFuIGltYWdl")
