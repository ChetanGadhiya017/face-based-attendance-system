"""Face detection and recognition with OpenCV's YuNet + SFace models.

* YuNet (230 KB) finds faces and five landmarks.
* SFace (37 MB) turns an aligned face into a 128-d embedding.
* Two faces belong to the same person when the cosine similarity of their
  embeddings is above a threshold (OpenCV recommends 0.363).

Only embeddings and a small thumbnail are stored, never full photos.
Models are downloaded once into ``MODELS_DIR`` and verified by SHA-256.
"""

from __future__ import annotations

import base64
import hashlib
import os
import threading
import urllib.request
from dataclasses import dataclass

import cv2
import numpy as np

MODELS = {
    "detector": (
        "face_detection_yunet_2023mar.onnx",
        "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/"
        "face_detection_yunet_2023mar.onnx",
        "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4",
    ),
    "recognizer": (
        "face_recognition_sface_2021dec.onnx",
        "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_recognition_sface/"
        "face_recognition_sface_2021dec.onnx",
        "0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79",
    ),
}


class FaceError(ValueError):
    """User-facing problem with an image (no face, several faces, unreadable…)."""


@dataclass
class DetectedFace:
    box: tuple[int, int, int, int]  # x, y, w, h in image pixels
    score: float
    embedding: np.ndarray            # L2-normalised float32[128]
    crop: np.ndarray                 # aligned 112×112 BGR face


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_models(models_dir: str, log=print) -> dict[str, str]:
    """Download missing models and verify checksums. Returns name → path."""
    os.makedirs(models_dir, exist_ok=True)
    paths = {}
    for key, (fname, url, sha) in MODELS.items():
        path = os.path.join(models_dir, fname)
        if not os.path.exists(path) or _sha256(path) != sha:
            log(f"Downloading {fname} …")
            tmp = path + ".part"
            urllib.request.urlretrieve(url, tmp)  # noqa: S310 - fixed https URL
            if _sha256(tmp) != sha:
                os.remove(tmp)
                raise RuntimeError(f"Checksum mismatch for {fname}")
            os.replace(tmp, path)
        paths[key] = path
    return paths


def decode_image(data: str | bytes) -> np.ndarray:
    """Accepts raw bytes or a ``data:image/...;base64,`` URL from the browser."""
    if isinstance(data, str):
        if "," in data[:100]:
            data = data.split(",", 1)[1]
        try:
            data = base64.b64decode(data, validate=False)
        except (ValueError, TypeError) as exc:
            raise FaceError("Image data is not valid base64") from exc
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise FaceError("Could not read the image (use JPEG or PNG)")
    return img


def thumbnail_jpeg(crop: np.ndarray, size: int = 96) -> bytes:
    ok, buf = cv2.imencode(".jpg", cv2.resize(crop, (size, size)), [cv2.IMWRITE_JPEG_QUALITY, 85])
    return buf.tobytes() if ok else b""


class FaceEngine:
    """Thread-safe lazy wrapper around the two OpenCV models."""

    def __init__(self, models_dir: str, score_threshold: float = 0.85, max_width: int = 960):
        self.models_dir = models_dir
        self.score_threshold = score_threshold
        self.max_width = max_width
        self._lock = threading.Lock()
        self._detector = None
        self._recognizer = None

    @property
    def available(self) -> bool:
        return all(os.path.exists(os.path.join(self.models_dir, f)) for f, _, _ in MODELS.values())

    def _load(self) -> None:
        if self._detector is None:
            if not self.available:
                raise FaceError("Face models are not installed. Run: flask --app wsgi download-models")
            d = os.path.join(self.models_dir, MODELS["detector"][0])
            r = os.path.join(self.models_dir, MODELS["recognizer"][0])
            self._detector = cv2.FaceDetectorYN.create(d, "", (320, 320), self.score_threshold, 0.3, 5000)
            self._recognizer = cv2.FaceRecognizerSF.create(r, "")

    def analyze(self, img: np.ndarray) -> list[DetectedFace]:
        """Detect every face and compute its embedding. Largest faces first."""
        scale = 1.0
        if img.shape[1] > self.max_width:
            scale = self.max_width / img.shape[1]
            img = cv2.resize(img, None, fx=scale, fy=scale)
        with self._lock:  # OpenCV DNN objects are not thread-safe
            self._load()
            h, w = img.shape[:2]
            self._detector.setInputSize((w, h))
            _, faces = self._detector.detect(img)
            out = []
            for f in faces if faces is not None else []:
                crop = self._recognizer.alignCrop(img, f)
                emb = self._recognizer.feature(crop).flatten().astype(np.float32)
                emb /= np.linalg.norm(emb) + 1e-9
                x, y, bw, bh = (f[:4] / scale).astype(int).tolist()
                out.append(DetectedFace((x, y, bw, bh), float(f[-1]), emb, crop))
        return sorted(out, key=lambda d: d.box[2] * d.box[3], reverse=True)

    def single_face(self, img: np.ndarray) -> DetectedFace:
        faces = self.analyze(img)
        if not faces:
            raise FaceError("No face found. Face the camera in good light.")
        if len(faces) > 1:
            big, second = faces[0].box, faces[1].box
            if big[2] * big[3] < 2.5 * second[2] * second[3]:
                raise FaceError("More than one face in the picture. Only the student should be visible.")
        f = faces[0]
        if f.box[2] < 60:
            raise FaceError("Face is too small. Move closer to the camera.")
        return f


def best_match(embedding: np.ndarray, gallery: dict[int, np.ndarray], threshold: float,
               margin: float = 0.05) -> tuple[int | None, float]:
    """Return (student_id, similarity) of the best match, or (None, best score).

    ``gallery`` maps student id → (n_samples, 128) matrix of normalised embeddings;
    a student's score is the max over their samples. A match must reach
    ``threshold`` *and* beat the runner-up student by ``margin`` so that two
    similar-looking classmates are never confused.
    """
    scores = sorted(((float(np.max(mat @ embedding)), sid) for sid, mat in gallery.items() if len(mat)),
                    reverse=True)
    if not scores:
        return None, 0.0
    best, sid = scores[0]
    runner_up = scores[1][0] if len(scores) > 1 else -1.0
    if best >= threshold and best - runner_up >= margin:
        return sid, best
    return None, best
