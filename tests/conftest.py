import base64

import cv2
import numpy as np
import pytest

from attendance import create_app
from attendance.config import TestConfig
from attendance.extensions import db
from attendance.face import DetectedFace, FaceError
from attendance.models import Course, Department, Enrollment, Student, User


def person_image(*people: int) -> str:
    """A tiny PNG whose first pixels encode which 'people' are in the frame (fake engine reads them)."""
    img = np.zeros((40, 40, 3), np.uint8)
    for i, p in enumerate(people):
        img[0, i] = (p, p, p)
    ok, buf = cv2.imencode(".png", img)
    return "data:image/png;base64," + base64.b64encode(buf.tobytes()).decode()


class FakeEngine:
    """Person k (1..127) → unit vector e_k. Pixel value 200+k → a near-duplicate of person k."""

    available = True

    def _emb(self, code: int) -> np.ndarray:
        v = np.zeros(128, np.float32)
        if code >= 200:
            v[code - 200] = 0.8
            v[127] = 0.6
        else:
            v[code] = 1.0
        return v / np.linalg.norm(v)

    def analyze(self, img):
        faces = []
        for i in range(img.shape[1]):
            code = int(img[0, i, 0])
            if code == 0:
                break
            faces.append(DetectedFace((10 + 60 * i, 10, 80, 80), 0.95, self._emb(code), np.zeros((112, 112, 3), np.uint8)))
        return faces

    def single_face(self, img):
        faces = self.analyze(img)
        if not faces:
            raise FaceError("No face found.")
        if len(faces) > 1:
            raise FaceError("More than one face in the picture.")
        return faces[0]


@pytest.fixture
def app():
    app = create_app(TestConfig)
    app.extensions["face_engine"] = FakeEngine()
    with app.app_context():
        dept = Department(code="CSE", name="Computer Science")
        admin = User(email="admin@x.io", name="Ada Admin", role="admin")
        admin.set_password("adminpass1")
        fac = User(email="fac@x.io", name="Frank Faculty", role="faculty")
        fac.set_password("facpass12")
        other = User(email="other@x.io", name="Olga Other", role="faculty")
        other.set_password("otherpass1")
        studs = [Student(roll_no=f"23BCP00{i}", name=f"Student {i}", department=dept, division="D1") for i in range(1, 5)]
        db.session.add_all([dept, admin, fac, other, *studs])
        c1 = Course(code="CS101", name="Algorithms", department=dept, faculty=fac)
        c2 = Course(code="CS102", name="Networks", department=dept, faculty=other)
        db.session.add_all([c1, c2])
        db.session.flush()
        for s in studs[:3]:
            db.session.add(Enrollment(student=s, course=c1))
        su = User(email="stud@x.io", name="Student 1", role="student", student_id=studs[0].id)
        su.set_password("studpass1")
        db.session.add(su)
        db.session.commit()
        yield app


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, email, pw):
    return client.post("/login", data={"email": email, "password": pw})


@pytest.fixture
def admin(client):
    login(client, "admin@x.io", "adminpass1")
    return client


@pytest.fixture
def faculty(client):
    login(client, "fac@x.io", "facpass12")
    return client
