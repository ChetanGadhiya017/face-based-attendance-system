"""Database models.

Mirrors the original DBMS design (department → students, courses → enrollments →
attendance) and adds users/roles, class sessions and face embeddings.
"""

from __future__ import annotations

from datetime import date, datetime

import numpy as np
from flask_login import UserMixin
from sqlalchemy import CheckConstraint, UniqueConstraint, func
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db

ROLES = ("admin", "faculty", "student")
STATUSES = ("present", "late", "absent")


def local_now() -> datetime:
    """Naive local time: attendance is read by people in the institute's own timezone."""
    return datetime.now()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(10), nullable=False, default="faculty")
    student_id = db.Column(db.Integer, db.ForeignKey("student.id", ondelete="SET NULL"))
    is_active_flag = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=local_now)
    last_login = db.Column(db.DateTime)

    student = db.relationship("Student", foreign_keys=[student_id])

    __table_args__ = (CheckConstraint(f"role IN {ROLES}", name="ck_user_role"),)

    def set_password(self, pw: str) -> None:
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw: str) -> bool:
        return check_password_hash(self.password_hash, pw)

    @property
    def is_active(self) -> bool:  # Flask-Login
        return self.is_active_flag

    @property
    def initials(self) -> str:
        return "".join(p[0] for p in self.name.split()[:2]).upper()


class Department(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)


class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    roll_no = db.Column(db.String(20), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120))
    department_id = db.Column(db.Integer, db.ForeignKey("department.id"))
    year = db.Column(db.Integer, default=1)
    division = db.Column(db.String(10))
    created_at = db.Column(db.DateTime, default=local_now)

    department = db.relationship("Department")
    faces = db.relationship("FaceSample", back_populates="student", cascade="all, delete-orphan")
    enrollments = db.relationship("Enrollment", back_populates="student", cascade="all, delete-orphan")
    records = db.relationship("Attendance", back_populates="student", cascade="all, delete-orphan")

    @property
    def initials(self) -> str:
        return "".join(p[0] for p in self.name.split()[:2]).upper()


class FaceSample(db.Model):
    """A 128-d SFace embedding (L2-normalised) plus a small thumbnail for review."""

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id", ondelete="CASCADE"), nullable=False, index=True)
    embedding = db.Column(db.LargeBinary, nullable=False)
    thumbnail = db.Column(db.LargeBinary)  # JPEG, ~96 px
    score = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=local_now)

    student = db.relationship("Student", back_populates="faces")

    @property
    def vector(self) -> np.ndarray:
        return np.frombuffer(self.embedding, dtype=np.float32)


class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey("department.id"))
    faculty_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"))
    created_at = db.Column(db.DateTime, default=local_now)

    department = db.relationship("Department")
    faculty = db.relationship("User")
    enrollments = db.relationship("Enrollment", back_populates="course", cascade="all, delete-orphan")
    sessions = db.relationship("ClassSession", back_populates="course", cascade="all, delete-orphan",
                               order_by="ClassSession.started_at.desc()")

    @property
    def students(self) -> list[Student]:
        return sorted((e.student for e in self.enrollments), key=lambda s: s.roll_no)


class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id", ondelete="CASCADE"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("course.id", ondelete="CASCADE"), nullable=False)

    student = db.relationship("Student", back_populates="enrollments")
    course = db.relationship("Course", back_populates="enrollments")
    __table_args__ = (UniqueConstraint("student_id", "course_id", name="uq_enrollment"),)


class ClassSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("course.id", ondelete="CASCADE"), nullable=False, index=True)
    topic = db.Column(db.String(200))
    date = db.Column(db.Date, default=date.today, nullable=False, index=True)
    started_at = db.Column(db.DateTime, default=local_now, nullable=False)
    ended_at = db.Column(db.DateTime)
    created_by = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"))

    course = db.relationship("Course", back_populates="sessions")
    records = db.relationship("Attendance", back_populates="session", cascade="all, delete-orphan")

    @property
    def is_open(self) -> bool:
        return self.ended_at is None

    def summary(self) -> dict:
        counts = {s: 0 for s in STATUSES}
        for r in self.records:
            counts[r.status] += 1
        total = len(self.course.enrollments)
        attended = counts["present"] + counts["late"]
        counts["unmarked"] = max(0, total - sum(counts.values()))
        counts["total"] = total
        counts["percent"] = round(100 * attended / total, 1) if total else 0.0
        return counts


class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("class_session.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id", ondelete="CASCADE"), nullable=False, index=True)
    status = db.Column(db.String(10), nullable=False, default="present")
    method = db.Column(db.String(10), nullable=False, default="face")  # face | manual | auto
    confidence = db.Column(db.Float)
    marked_at = db.Column(db.DateTime, default=local_now)
    marked_by = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"))

    session = db.relationship("ClassSession", back_populates="records")
    student = db.relationship("Student", back_populates="records")
    __table_args__ = (
        UniqueConstraint("session_id", "student_id", name="uq_attendance_once"),
        CheckConstraint(f"status IN {STATUSES}", name="ck_attendance_status"),
    )


# ------------------------------------------------------------------ queries used by several views
def attendance_stats(course_id: int | None = None, student_id: int | None = None) -> list[dict]:
    """Per (student, course): sessions held, attended (present+late), late count and percentage.

    Sessions held = closed sessions of the course after the student enrolled (all closed sessions here).
    """
    held = (
        db.session.query(ClassSession.course_id, func.count(ClassSession.id).label("held"))
        .filter(ClassSession.ended_at.isnot(None))
        .group_by(ClassSession.course_id)
        .subquery()
    )
    attended = (
        db.session.query(
            Attendance.student_id, ClassSession.course_id,
            func.sum(db.case((Attendance.status.in_(("present", "late")), 1), else_=0)).label("attended"),
            func.sum(db.case((Attendance.status == "late", 1), else_=0)).label("late"),
        )
        .join(ClassSession, ClassSession.id == Attendance.session_id)
        .filter(ClassSession.ended_at.isnot(None))
        .group_by(Attendance.student_id, ClassSession.course_id)
        .subquery()
    )
    q = (
        db.session.query(Enrollment.student_id, Enrollment.course_id,
                         func.coalesce(held.c.held, 0), func.coalesce(attended.c.attended, 0),
                         func.coalesce(attended.c.late, 0))
        .outerjoin(held, held.c.course_id == Enrollment.course_id)
        .outerjoin(attended, (attended.c.student_id == Enrollment.student_id) & (attended.c.course_id == Enrollment.course_id))
    )
    if course_id:
        q = q.filter(Enrollment.course_id == course_id)
    if student_id:
        q = q.filter(Enrollment.student_id == student_id)
    out = []
    for sid, cid, h, a, late in q.all():
        out.append({"student_id": sid, "course_id": cid, "held": int(h), "attended": int(a), "late": int(late),
                    "percent": round(100 * a / h, 1) if h else None})
    return out
