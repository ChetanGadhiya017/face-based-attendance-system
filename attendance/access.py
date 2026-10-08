"""Role checks and per-object permissions."""

from __future__ import annotations

from functools import wraps

from flask import abort
from flask_login import current_user, login_required

from .extensions import db
from .models import ClassSession, Course


def roles_required(*roles):
    def deco(fn):
        @wraps(fn)
        @login_required
        def wrapper(*a, **kw):
            if current_user.role not in roles:
                abort(403)
            return fn(*a, **kw)
        return wrapper
    return deco


staff_required = roles_required("admin", "faculty")
admin_required = roles_required("admin")


def visible_courses():
    q = Course.query.order_by(Course.code)
    if current_user.role == "faculty":
        q = q.filter(Course.faculty_id == current_user.id)
    return q


def get_course_or_403(course_id: int) -> Course:
    c = db.get_or_404(Course, course_id)
    if current_user.role == "faculty" and c.faculty_id != current_user.id:
        abort(403)
    return c


def get_session_or_403(session_id: int) -> ClassSession:
    s = db.get_or_404(ClassSession, session_id)
    get_course_or_403(s.course_id)
    return s
