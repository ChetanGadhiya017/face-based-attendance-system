"""JSON endpoints used by the camera pages (same-origin, session auth + CSRF header)."""

from __future__ import annotations

import base64

from flask import Blueprint, jsonify, request
from flask_login import current_user

from . import services
from .access import get_session_or_403, staff_required
from .extensions import db
from .face import FaceError
from .models import FaceSample, Student

bp = Blueprint("api", __name__)


def _image():
    data = request.get_json(silent=True) or {}
    img = data.get("image")
    if not img or not isinstance(img, str):
        raise FaceError("Send an image as a data URL in the 'image' field")
    return img


@bp.errorhandler(FaceError)
def face_error(exc):
    return jsonify(error=str(exc)), 422


@bp.errorhandler(ValueError)
def value_error(exc):
    return jsonify(error=str(exc)), 400


@bp.get("/health")
def health():
    from flask import current_app

    return jsonify(status="ok", face_models=current_app.extensions["face_engine"].available)


@bp.post("/sessions/<int:sid>/recognize")
@staff_required
def recognize(sid: int):
    session = get_session_or_403(sid)
    return jsonify(services.recognize_frame(session, _image(), current_user))


@bp.get("/sessions/<int:sid>/roster")
@staff_required
def roster(sid: int):
    session = get_session_or_403(sid)
    recs = {r.student_id: r for r in session.records}
    rows = []
    for st in session.course.students:
        r = recs.get(st.id)
        rows.append({"id": st.id, "name": st.name, "roll_no": st.roll_no, "has_face": bool(st.faces),
                     "status": r.status if r else None, "method": r.method if r else None,
                     "time": r.marked_at.strftime("%H:%M:%S") if r and r.marked_at else None})
    return jsonify(students=rows, summary=session.summary(), open=session.is_open)


@bp.post("/sessions/<int:sid>/mark")
@staff_required
def mark(sid: int):
    session = get_session_or_403(sid)
    data = request.get_json(silent=True) or {}
    rec = services.mark(session, int(data.get("student_id", 0)), data.get("status", ""), "manual", user=current_user)
    return jsonify(status=rec.status, summary=session.summary())


@bp.post("/students/<int:student_id>/faces")
@staff_required
def add_face(student_id: int):
    st = db.get_or_404(Student, student_id)
    sample = services.add_face_sample(st, _image())
    return jsonify(id=sample.id, count=len(st.faces),
                   thumbnail="data:image/jpeg;base64," + base64.b64encode(sample.thumbnail or b"").decode()), 201


@bp.delete("/students/<int:student_id>/faces/<int:face_id>")
@staff_required
def delete_face(student_id: int, face_id: int):
    f = db.get_or_404(FaceSample, face_id)
    if f.student_id != student_id:
        return jsonify(error="Not found"), 404
    db.session.delete(f)
    db.session.commit()
    return jsonify(ok=True)
