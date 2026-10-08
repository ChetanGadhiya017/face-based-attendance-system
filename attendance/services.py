"""Attendance business logic shared by the web views, the JSON API and tests."""

from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
from flask import current_app

from .extensions import db
from .face import FaceError, best_match, decode_image, thumbnail_jpeg
from .models import Attendance, ClassSession, Enrollment, FaceSample, Student, local_now


def engine():
    return current_app.extensions["face_engine"]


# ------------------------------------------------------------------ enrollment of faces
def add_face_sample(student: Student, image) -> FaceSample:
    if len(student.faces) >= current_app.config["MAX_FACE_SAMPLES"]:
        raise FaceError(f"This student already has {len(student.faces)} samples. Delete one first.")
    face = engine().single_face(decode_image(image) if not isinstance(image, np.ndarray) else image)
    # Reject a sample that matches *another* student strongly (wrong person selected).
    others = gallery_for([s for s in Student.query.filter(Student.id != student.id).all() if s.faces])
    sid, score = best_match(face.embedding, others, current_app.config["RECOGNITION_THRESHOLD"] + 0.1, 0.0)
    if sid is not None:
        other = db.session.get(Student, sid)
        raise FaceError(f"This face looks like {other.name} ({other.roll_no}). Check you selected the right student.")
    sample = FaceSample(student=student, embedding=face.embedding.astype(np.float32).tobytes(),
                        thumbnail=thumbnail_jpeg(face.crop), score=face.score)
    db.session.add(sample)
    db.session.commit()
    return sample


def gallery_for(students) -> dict[int, np.ndarray]:
    return {s.id: np.stack([f.vector for f in s.faces]) for s in students if s.faces}


# ------------------------------------------------------------------ sessions
def start_session(course, user, topic: str = "") -> ClassSession:
    open_ = ClassSession.query.filter_by(course_id=course.id, ended_at=None).first()
    if open_:
        return open_
    s = ClassSession(course=course, topic=topic.strip()[:200] or None, created_by=user.id,
                     started_at=local_now(), date=datetime.now().date())
    db.session.add(s)
    db.session.commit()
    return s


def close_session(session: ClassSession) -> int:
    """Close and mark every unmarked enrolled student absent. Returns number marked absent."""
    if not session.is_open:
        return 0
    marked = {r.student_id for r in session.records}
    n = 0
    for e in session.course.enrollments:
        if e.student_id not in marked:
            db.session.add(Attendance(session=session, student_id=e.student_id, status="absent", method="auto"))
            n += 1
    session.ended_at = local_now()
    db.session.commit()
    return n


def mark(session: ClassSession, student_id: int, status: str, method: str = "manual",
         confidence: float | None = None, user=None) -> Attendance:
    if status not in ("present", "late", "absent"):
        raise ValueError("Invalid status")
    if not Enrollment.query.filter_by(course_id=session.course_id, student_id=student_id).first():
        raise ValueError("Student is not enrolled in this course")
    rec = Attendance.query.filter_by(session_id=session.id, student_id=student_id).first()
    if rec is None:
        rec = Attendance(session=session, student_id=student_id)
        db.session.add(rec)
    rec.status, rec.method, rec.confidence = status, method, confidence
    rec.marked_at = local_now()
    rec.marked_by = getattr(user, "id", None)
    db.session.commit()
    return rec


def recognize_frame(session: ClassSession, image, user=None) -> dict:
    """Detect faces in a webcam frame and mark recognised, enrolled students present (or late)."""
    if not session.is_open:
        raise FaceError("This session is closed.")
    cfg = current_app.config
    img = decode_image(image) if not isinstance(image, np.ndarray) else image
    faces = engine().analyze(img)
    students = [e.student for e in session.course.enrollments]
    gallery = gallery_for(students)
    by_id = {s.id: s for s in students}
    already = {r.student_id: r for r in session.records}
    late_cutoff = session.started_at + timedelta(minutes=cfg["LATE_AFTER_MINUTES"])

    results = []
    for f in faces:
        sid, score = best_match(f.embedding, gallery, cfg["RECOGNITION_THRESHOLD"], cfg["RECOGNITION_MARGIN"])
        item = {"box": list(f.box), "score": round(score, 3)}
        if sid is None:
            item.update(status="unknown")
        else:
            st = by_id[sid]
            item.update(student_id=sid, name=st.name, roll_no=st.roll_no)
            prev = already.get(sid)
            if prev and prev.status in ("present", "late"):
                item["status"] = "already"
            else:
                status = "late" if local_now() > late_cutoff else "present"
                mark(session, sid, status, method="face", confidence=score, user=user)
                item["status"] = "marked"
                item["marked_as"] = status
        results.append(item)
    return {"faces": results, "frame": {"w": int(img.shape[1]), "h": int(img.shape[0])},
            "summary": session.summary(), "enrolled_without_face": sum(1 for s in students if not s.faces)}
