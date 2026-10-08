"""Server-rendered pages."""

from __future__ import annotations

import base64
import csv
import io
from collections import defaultdict
from datetime import date, timedelta

from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import func, or_

from . import services
from .access import admin_required, get_course_or_403, get_session_or_403, staff_required, visible_courses
from .extensions import db
from .models import (
    ROLES,
    Attendance,
    ClassSession,
    Course,
    Department,
    Enrollment,
    FaceSample,
    Student,
    User,
    attendance_stats,
)

bp = Blueprint("main", __name__)
PER_PAGE = 25


def b64(data: bytes | None) -> str:
    return "data:image/jpeg;base64," + base64.b64encode(data or b"").decode()


@bp.app_template_global()
def thumb(face: FaceSample) -> str:
    return b64(face.thumbnail)


def _int(v, default=None):
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


# ================================================================== home & dashboard
@bp.get("/")
@login_required
def home():
    if current_user.role == "student":
        return redirect(url_for("main.portal"))
    return redirect(url_for("main.dashboard"))


@bp.get("/dashboard")
@staff_required
def dashboard():
    courses = visible_courses().all()
    cids = [c.id for c in courses]
    min_pct = current_app.config["MIN_ATTENDANCE_PERCENT"]
    stats = [s for s in attendance_stats() if s["course_id"] in cids]

    # per-course average and defaulters
    by_course = defaultdict(list)
    for s in stats:
        if s["percent"] is not None:
            by_course[s["course_id"]].append(s["percent"])
    course_avg = {cid: round(sum(v) / len(v), 1) for cid, v in by_course.items() if v}
    students = {s.id: s for s in Student.query.filter(Student.id.in_({x["student_id"] for x in stats})).all()} if stats else {}
    course_map = {c.id: c for c in courses}
    defaulters = sorted((s for s in stats if s["percent"] is not None and s["percent"] < min_pct), key=lambda s: s["percent"])
    defaulters = [dict(s, student=students[s["student_id"]], course=course_map[s["course_id"]]) for s in defaulters[:12]]

    # daily trend for the last 21 days
    since = date.today() - timedelta(days=21)
    rows = (
        db.session.query(ClassSession.date,
                         func.sum(db.case((Attendance.status.in_(("present", "late")), 1), else_=0)),
                         func.count(Attendance.id))
        .join(Attendance, Attendance.session_id == ClassSession.id)
        .filter(ClassSession.course_id.in_(cids or [-1]), ClassSession.date >= since, ClassSession.ended_at.isnot(None))
        .group_by(ClassSession.date).order_by(ClassSession.date).all()
    )
    trend = {"labels": [d.strftime("%d %b") for d, _, _ in rows],
             "values": [round(100 * a / t, 1) if t else 0 for _, a, t in rows]}

    method_rows = (
        db.session.query(Attendance.method, func.count(Attendance.id))
        .join(ClassSession).filter(ClassSession.course_id.in_(cids or [-1]), Attendance.status != "absent")
        .group_by(Attendance.method).all()
    )
    open_sessions = ClassSession.query.filter(ClassSession.course_id.in_(cids or [-1]), ClassSession.ended_at.is_(None)).all()
    recent = (ClassSession.query.filter(ClassSession.course_id.in_(cids or [-1]), ClassSession.ended_at.isnot(None))
              .order_by(ClassSession.started_at.desc()).limit(6).all())
    all_pct = [s["percent"] for s in stats if s["percent"] is not None]
    kpis = {
        "students": len({s["student_id"] for s in stats}),
        "courses": len(courses),
        "sessions": ClassSession.query.filter(ClassSession.course_id.in_(cids or [-1])).count(),
        "average": round(sum(all_pct) / len(all_pct), 1) if all_pct else None,
        "below": len({s["student_id"] for s in stats if s["percent"] is not None and s["percent"] < min_pct}),
        "no_face": Student.query.filter(~Student.faces.any()).count(),
    }
    return render_template("dashboard.html", courses=courses, course_avg=course_avg, defaulters=defaulters, trend=trend,
                           methods=dict(method_rows), open_sessions=open_sessions, recent=recent, kpis=kpis)


# ================================================================== students
def _student_query():
    q = Student.query
    if current_user.role == "faculty":
        q = q.join(Enrollment).join(Course).filter(Course.faculty_id == current_user.id).distinct()
    return q


@bp.get("/students")
@staff_required
def students():
    q = _student_query()
    term = request.args.get("q", "").strip()
    dept = _int(request.args.get("dept"))
    face = request.args.get("face", "")
    if term:
        like = f"%{term}%"
        q = q.filter(or_(Student.name.ilike(like), Student.roll_no.ilike(like), Student.email.ilike(like)))
    if dept:
        q = q.filter(Student.department_id == dept)
    if face == "yes":
        q = q.filter(Student.faces.any())
    elif face == "no":
        q = q.filter(~Student.faces.any())
    page = q.order_by(Student.roll_no).paginate(page=_int(request.args.get("page"), 1), per_page=PER_PAGE, error_out=False)
    return render_template("students/list.html", page=page, depts=Department.query.order_by(Department.code).all(),
                           q=term, dept=dept, face=face)


def _student_from_form(st: Student) -> list[str]:
    errors = []
    f = request.form
    st.roll_no = f.get("roll_no", "").strip().upper()
    st.name = " ".join(f.get("name", "").split())
    st.email = f.get("email", "").strip().lower() or None
    st.department_id = _int(f.get("department_id"))
    st.year = _int(f.get("year"), 1)
    st.division = f.get("division", "").strip().upper() or None
    if not st.roll_no or len(st.roll_no) > 20:
        errors.append("Roll number is required (max 20 characters).")
    if not st.name:
        errors.append("Name is required.")
    dup = Student.query.filter(Student.roll_no == st.roll_no, Student.id != (st.id or 0)).first()
    if dup:
        errors.append(f"Roll number {st.roll_no} already belongs to {dup.name}.")
    if st.email and "@" not in st.email:
        errors.append("Email address looks invalid.")
    return errors


@bp.route("/students/new", methods=["GET", "POST"])
@admin_required
def student_new():
    st = Student()
    if request.method == "POST":
        errors = _student_from_form(st)
        if not errors:
            db.session.add(st)
            db.session.commit()
            flash(f"Added {st.name}. Now enrol their face.", "success")
            return redirect(url_for("main.student_detail", sid=st.id))
        for e in errors:
            flash(e, "error")
    return render_template("students/form.html", st=st, depts=Department.query.order_by(Department.code).all())


@bp.route("/students/<int:sid>/edit", methods=["GET", "POST"])
@admin_required
def student_edit(sid: int):
    st = db.get_or_404(Student, sid)
    if request.method == "POST":
        errors = _student_from_form(st)
        if not errors:
            db.session.commit()
            flash("Student updated.", "success")
            return redirect(url_for("main.student_detail", sid=st.id))
        db.session.rollback()
        for e in errors:
            flash(e, "error")
    return render_template("students/form.html", st=st, depts=Department.query.order_by(Department.code).all())


@bp.post("/students/<int:sid>/delete")
@admin_required
def student_delete(sid: int):
    st = db.get_or_404(Student, sid)
    db.session.delete(st)
    db.session.commit()
    flash(f"Deleted {st.name} and their attendance records.", "info")
    return redirect(url_for("main.students"))


@bp.get("/students/<int:sid>")
@staff_required
def student_detail(sid: int):
    st = db.get_or_404(Student, sid)
    if current_user.role == "faculty" and not _student_query().filter(Student.id == sid).first():
        abort(403)
    stats = attendance_stats(student_id=sid)
    courses = {c.id: c for c in Course.query.filter(Course.id.in_([s["course_id"] for s in stats] or [-1]))}
    recent = (Attendance.query.filter_by(student_id=sid).join(ClassSession)
              .order_by(ClassSession.started_at.desc()).limit(15).all())
    return render_template("students/detail.html", st=st, stats=stats, courses=courses, recent=recent,
                           max_faces=current_app.config["MAX_FACE_SAMPLES"],
                           models_ready=current_app.extensions["face_engine"].available)


@bp.route("/students/import", methods=["GET", "POST"])
@admin_required
def student_import():
    if request.method == "POST":
        file = request.files.get("file")
        if not file or not file.filename.lower().endswith(".csv"):
            flash("Choose a .csv file.", "error")
            return redirect(request.url)
        text = file.read().decode("utf-8-sig", errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        depts = {d.code.upper(): d for d in Department.query.all()}
        added = updated = 0
        problems = []
        for i, row in enumerate(reader, start=2):
            row = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
            roll, name = row.get("roll_no", "").upper(), row.get("name", "")
            if not roll or not name:
                problems.append(f"Row {i}: roll_no and name are required")
                continue
            st = Student.query.filter_by(roll_no=roll).first()
            if st:
                updated += 1
            else:
                st = Student(roll_no=roll)
                db.session.add(st)
                added += 1
            st.name, st.email = name, row.get("email") or st.email
            st.year = _int(row.get("year"), st.year or 1)
            st.division = row.get("division") or st.division
            code = row.get("department", "").upper()
            if code:
                if code not in depts:
                    depts[code] = Department(code=code, name=code)
                    db.session.add(depts[code])
                st.department = depts[code]
        db.session.commit()
        flash(f"Imported: {added} added, {updated} updated.", "success")
        for p in problems[:10]:
            flash(p, "error")
        return redirect(url_for("main.students"))
    return render_template("students/import.html")


@bp.get("/students/template.csv")
@admin_required
def student_template():
    return Response("roll_no,name,email,department,year,division\n23BCP101,Sample Student,sample@college.edu,CSE,3,D1\n",
                    mimetype="text/csv", headers={"Content-Disposition": 'attachment; filename="students-template.csv"'})


# ================================================================== courses
@bp.get("/courses")
@staff_required
def courses():
    cs = visible_courses().all()
    avg = defaultdict(list)
    for s in attendance_stats():
        if s["percent"] is not None:
            avg[s["course_id"]].append(s["percent"])
    course_avg = {k: round(sum(v) / len(v), 1) for k, v in avg.items()}
    return render_template("courses/list.html", courses=cs, course_avg=course_avg)


def _course_from_form(c: Course) -> list[str]:
    f = request.form
    c.code = f.get("code", "").strip().upper()
    c.name = " ".join(f.get("name", "").split())
    c.department_id = _int(f.get("department_id"))
    c.faculty_id = _int(f.get("faculty_id"))
    errors = []
    if not c.code or not c.name:
        errors.append("Course code and name are required.")
    if Course.query.filter(Course.code == c.code, Course.id != (c.id or 0)).first():
        errors.append(f"Course code {c.code} already exists.")
    return errors


@bp.route("/courses/new", methods=["GET", "POST"])
@admin_required
def course_new():
    c = Course()
    if request.method == "POST":
        errors = _course_from_form(c)
        if not errors:
            db.session.add(c)
            db.session.commit()
            flash("Course created. Now enrol students.", "success")
            return redirect(url_for("main.course_detail", cid=c.id))
        for e in errors:
            flash(e, "error")
    return render_template("courses/form.html", c=c, depts=Department.query.all(),
                           faculty=User.query.filter(User.role.in_(("faculty", "admin"))).order_by(User.name).all())


@bp.route("/courses/<int:cid>/edit", methods=["GET", "POST"])
@admin_required
def course_edit(cid: int):
    c = db.get_or_404(Course, cid)
    if request.method == "POST":
        errors = _course_from_form(c)
        if not errors:
            db.session.commit()
            flash("Course updated.", "success")
            return redirect(url_for("main.course_detail", cid=c.id))
        db.session.rollback()
        for e in errors:
            flash(e, "error")
    return render_template("courses/form.html", c=c, depts=Department.query.all(),
                           faculty=User.query.filter(User.role.in_(("faculty", "admin"))).order_by(User.name).all())


@bp.post("/courses/<int:cid>/delete")
@admin_required
def course_delete(cid: int):
    c = db.get_or_404(Course, cid)
    db.session.delete(c)
    db.session.commit()
    flash(f"Deleted course {c.code}.", "info")
    return redirect(url_for("main.courses"))


@bp.get("/courses/<int:cid>")
@staff_required
def course_detail(cid: int):
    c = get_course_or_403(cid)
    stats = {s["student_id"]: s for s in attendance_stats(course_id=cid)}
    divisions = [d for (d,) in db.session.query(Student.division).distinct().order_by(Student.division) if d]
    return render_template("courses/detail.html", c=c, stats=stats, divisions=divisions,
                           depts=Department.query.order_by(Department.code).all(),
                           open_session=next((s for s in c.sessions if s.is_open), None))


@bp.post("/courses/<int:cid>/enroll")
@staff_required
def course_enroll(cid: int):
    c = get_course_or_403(cid)
    q = Student.query
    mode = request.form.get("mode")
    if mode == "division":
        q = q.filter(Student.division == request.form.get("division"))
    elif mode == "department":
        q = q.filter(Student.department_id == _int(request.form.get("department_id")))
    elif mode == "rolls":
        rolls = {r.strip().upper() for r in request.form.get("rolls", "").replace(",", "\n").splitlines() if r.strip()}
        q = q.filter(Student.roll_no.in_(rolls or {""}))
    elif mode != "all":
        abort(400)
    existing = {e.student_id for e in c.enrollments}
    n = 0
    for st in q.all():
        if st.id not in existing:
            db.session.add(Enrollment(student=st, course=c))
            n += 1
    db.session.commit()
    flash(f"Enrolled {n} student(s).", "success")
    return redirect(url_for("main.course_detail", cid=cid))


@bp.post("/courses/<int:cid>/unenroll/<int:sid>")
@staff_required
def course_unenroll(cid: int, sid: int):
    get_course_or_403(cid)
    e = Enrollment.query.filter_by(course_id=cid, student_id=sid).first_or_404()
    db.session.delete(e)
    db.session.commit()
    flash("Student removed from the course.", "info")
    return redirect(url_for("main.course_detail", cid=cid))


# ================================================================== sessions
@bp.post("/courses/<int:cid>/sessions")
@staff_required
def session_start(cid: int):
    c = get_course_or_403(cid)
    if not c.enrollments:
        flash("Enrol students before starting a session.", "error")
        return redirect(url_for("main.course_detail", cid=cid))
    s = services.start_session(c, current_user, request.form.get("topic", ""))
    return redirect(url_for("main.session_view", sid=s.id))


@bp.get("/sessions/<int:sid>")
@staff_required
def session_view(sid: int):
    s = get_session_or_403(sid)
    tpl = "sessions/live.html" if s.is_open else "sessions/detail.html"
    recs = {r.student_id: r for r in s.records}
    return render_template(tpl, s=s, recs=recs, models_ready=current_app.extensions["face_engine"].available)


@bp.post("/sessions/<int:sid>/close")
@staff_required
def session_close(sid: int):
    s = get_session_or_403(sid)
    n = services.close_session(s)
    flash(f"Session closed. {n} unmarked student(s) recorded as absent.", "success")
    return redirect(url_for("main.session_view", sid=sid))


@bp.post("/sessions/<int:sid>/delete")
@staff_required
def session_delete(sid: int):
    s = get_session_or_403(sid)
    cid = s.course_id
    db.session.delete(s)
    db.session.commit()
    flash("Session deleted.", "info")
    return redirect(url_for("main.course_detail", cid=cid))


@bp.post("/sessions/<int:sid>/mark/<int:student_id>")
@staff_required
def session_mark(sid: int, student_id: int):
    s = get_session_or_403(sid)
    try:
        services.mark(s, student_id, request.form.get("status", ""), "manual", user=current_user)
    except ValueError as exc:
        flash(str(exc), "error")
    return redirect(url_for("main.session_view", sid=sid) + f"#st-{student_id}")


@bp.get("/sessions/<int:sid>/export.csv")
@staff_required
def session_csv(sid: int):
    s = get_session_or_403(sid)
    recs = {r.student_id: r for r in s.records}
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["roll_no", "name", "status", "method", "marked_at", "confidence"])
    for st in s.course.students:
        r = recs.get(st.id)
        w.writerow([st.roll_no, st.name, r.status if r else "unmarked", r.method if r else "",
                    r.marked_at.strftime("%Y-%m-%d %H:%M:%S") if r and r.marked_at else "",
                    f"{r.confidence:.3f}" if r and r.confidence else ""])
    fname = f"{s.course.code}-{s.date.isoformat()}-attendance.csv"
    return Response(buf.getvalue(), mimetype="text/csv", headers={"Content-Disposition": f'attachment; filename="{fname}"'})


# ================================================================== reports
@bp.get("/reports")
@staff_required
def reports():
    courses = visible_courses().all()
    cid = _int(request.args.get("course")) or (courses[0].id if courses else None)
    course = get_course_or_403(cid) if cid else None
    rows, chart = [], {"labels": [], "values": []}
    min_pct = current_app.config["MIN_ATTENDANCE_PERCENT"]
    if course:
        stats = {s["student_id"]: s for s in attendance_stats(course_id=course.id)}
        for st in course.students:
            s = stats.get(st.id, {"held": 0, "attended": 0, "late": 0, "percent": None})
            need = None
            if s["percent"] is not None and s["percent"] < min_pct:
                # consecutive sessions needed to climb back to the minimum
                h, a = s["held"], s["attended"]
                need = max(0, -(-(min_pct * h - 100 * a) // (100 - min_pct)))
            rows.append({"student": st, **s, "need": need})
        filt = request.args.get("filter")
        if filt == "below":
            rows = [r for r in rows if r["percent"] is not None and r["percent"] < min_pct]
        sort = request.args.get("sort", "roll")
        if sort == "pct":
            rows.sort(key=lambda r: (r["percent"] is None, r["percent"] or 0))
        sessions = [s for s in reversed(course.sessions) if not s.is_open]
        chart = {"labels": [s.date.strftime("%d %b") for s in sessions], "values": [s.summary()["percent"] for s in sessions]}
    return render_template("reports.html", courses=courses, course=course, rows=rows, chart=chart)


@bp.get("/reports/course/<int:cid>.csv")
@staff_required
def report_csv(cid: int):
    c = get_course_or_403(cid)
    stats = {s["student_id"]: s for s in attendance_stats(course_id=cid)}
    sessions = [s for s in reversed(c.sessions) if not s.is_open]
    matrix = defaultdict(dict)
    for s in sessions:
        for r in s.records:
            matrix[r.student_id][s.id] = {"present": "P", "late": "L", "absent": "A"}[r.status]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["roll_no", "name", "held", "attended", "late", "percent"] + [s.date.isoformat() for s in sessions])
    for st in c.students:
        s = stats.get(st.id, {})
        w.writerow([st.roll_no, st.name, s.get("held", 0), s.get("attended", 0), s.get("late", 0),
                    s.get("percent", "")] + [matrix[st.id].get(x.id, "") for x in sessions])
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="{c.code}-attendance-report.csv"'})


# ================================================================== student portal
@bp.get("/me")
@login_required
def portal():
    if current_user.role != "student" or not current_user.student:
        if current_user.role == "student":
            flash("Your account is not linked to a student record yet. Ask the administrator.", "error")
            return render_template("portal.html", st=None, stats=[], courses={}, recent=[])
        return redirect(url_for("main.dashboard"))
    st = current_user.student
    stats = attendance_stats(student_id=st.id)
    courses = {c.id: c for c in Course.query.filter(Course.id.in_([s["course_id"] for s in stats] or [-1]))}
    recent = (Attendance.query.filter_by(student_id=st.id).join(ClassSession)
              .order_by(ClassSession.started_at.desc()).limit(20).all())
    return render_template("portal.html", st=st, stats=stats, courses=courses, recent=recent)


# ================================================================== users (admin)
@bp.route("/users", methods=["GET", "POST"])
@admin_required
def users():
    if request.method == "POST":
        f = request.form
        email = f.get("email", "").strip().lower()
        role = f.get("role", "faculty")
        pw = f.get("password", "")
        if role not in ROLES or "@" not in email or len(pw) < 8 or not f.get("name", "").strip():
            flash("Name, a valid email, a role and a password of at least 8 characters are required.", "error")
        elif User.query.filter_by(email=email).first():
            flash("A user with that email already exists.", "error")
        else:
            u = User(email=email, name=f["name"].strip(), role=role)
            if role == "student":
                st = Student.query.filter_by(roll_no=f.get("roll_no", "").strip().upper()).first()
                if not st:
                    flash("For student accounts, enter an existing roll number.", "error")
                    return redirect(url_for("main.users"))
                u.student_id = st.id
            u.set_password(pw)
            db.session.add(u)
            db.session.commit()
            flash(f"Created {role} account for {u.name}.", "success")
        return redirect(url_for("main.users"))
    return render_template("users.html", users=User.query.order_by(User.role, User.name).all())


@bp.post("/users/<int:uid>/toggle")
@admin_required
def user_toggle(uid: int):
    u = db.get_or_404(User, uid)
    if u.id == current_user.id:
        flash("You cannot deactivate your own account.", "error")
    else:
        u.is_active_flag = not u.is_active_flag
        db.session.commit()
        flash(f"{u.name} is now {'active' if u.is_active_flag else 'deactivated'}.", "info")
    return redirect(url_for("main.users"))
