"""Management commands:  flask --app wsgi <command>"""

from __future__ import annotations

import random
from datetime import date, datetime, timedelta

import click

from .extensions import db
from .face import ensure_models
from .models import Attendance, ClassSession, Course, Department, Enrollment, Student, User

FIRST = ["Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Krishna", "Ishaan", "Rohan", "Ananya",
         "Diya", "Aadhya", "Saanvi", "Myra", "Kiara", "Isha", "Riya", "Meera", "Tara", "Kabir", "Dev", "Yash",
         "Nisha", "Priya", "Neel", "Om", "Jiya", "Avni", "Kavya", "Manav", "Parth", "Harsh", "Pooja", "Sneha"]
LAST = ["Shah", "Patel", "Mehta", "Desai", "Joshi", "Trivedi", "Pandya", "Bhatt", "Iyer", "Nair", "Rao", "Kapoor",
        "Verma", "Gupta", "Reddy", "Kulkarni", "Chauhan", "Rana", "Sheth", "Parikh"]
COURSES = [("20CP206T", "Theory of Computation"), ("20CP207T", "Operating Systems"),
           ("20CP208T", "Database Management Systems"), ("20CP209T", "Computer Networks")]
TOPICS = ["Introduction", "Finite automata", "Regular expressions", "Context-free grammars", "Pushdown automata",
          "Turing machines", "Process scheduling", "Deadlocks", "Paging", "Normalization", "Transactions",
          "Indexing", "TCP congestion control", "Routing", "Revision", "Quiz", "Case study", "Lab review"]


def register_cli(app):
    @app.cli.command("init-db")
    def init_db():
        """Create all tables."""
        db.create_all()
        click.echo("Database ready.")

    @app.cli.command("create-admin")
    @click.option("--email", prompt=True)
    @click.option("--name", default="Administrator")
    @click.password_option()
    def create_admin(email, name, password):
        """Create or reset an administrator account."""
        user = User.query.filter_by(email=email.lower()).first() or User(email=email.lower())
        user.name, user.role = name, "admin"
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"Admin ready: {user.email}")

    @app.cli.command("download-models")
    def download_models():
        """Download the YuNet + SFace face models (≈38 MB)."""
        paths = ensure_models(app.config["MODELS_DIR"], log=click.echo)
        app.extensions["face_engine"]._detector = None
        click.echo("Models ready: " + ", ".join(paths.values()))

    @app.cli.command("seed-demo")
    @click.option("--students", default=48, show_default=True)
    @click.option("--weeks", default=6, show_default=True)
    @click.option("--seed", default=7, show_default=True)
    def seed_demo(students, weeks, seed):
        """Fill the database with synthetic demo data (fake names, no photos)."""
        summary = seed_demo_data(students, weeks, seed)
        click.echo("Demo data created.")
        for line in summary:
            click.echo("  " + line)


def seed_demo_data(n_students: int = 48, weeks: int = 6, seed: int = 7) -> list[str]:
    rng = random.Random(seed)
    db.drop_all()
    db.create_all()

    cse = Department(code="CSE", name="Computer Science & Engineering")
    ict = Department(code="ICT", name="Information & Communication Technology")
    db.session.add_all([cse, ict])

    admin = User(email="admin@demo.local", name="Admin User", role="admin")
    admin.set_password("admin123")
    faculty = []
    for i, nm in enumerate(["Dr. Neha Sharma", "Prof. Rakesh Iyer", "Dr. Kavita Rao"], 1):
        u = User(email=f"faculty{i}@demo.local", name=nm, role="faculty")
        u.set_password("faculty123")
        faculty.append(u)
    db.session.add_all([admin, *faculty])

    names = set()
    studs = []
    while len(studs) < n_students:
        nm = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
        if nm in names:
            continue
        names.add(nm)
        k = len(studs) + 1
        studs.append(Student(roll_no=f"23BCP{k:03d}", name=nm, email=f"student{k:03d}@demo.local",
                             department=cse if k % 5 else ict, year=3, division=f"D{(k - 1) // 24 + 1}"))
    db.session.add_all(studs)
    courses = [Course(code=c, name=n, department=cse, faculty=faculty[i % len(faculty)]) for i, (c, n) in enumerate(COURSES)]
    db.session.add_all(courses)
    db.session.flush()
    for c in courses:
        for s in studs:
            db.session.add(Enrollment(student=s, course=c))

    portal = User(email="student@demo.local", name=studs[0].name, role="student", student_id=studs[0].id)
    portal.set_password("student123")
    db.session.add(portal)

    # Each student has a personal attendance tendency so reports show a realistic spread.
    tendency = {s.id: rng.choice([0.99, 0.97, 0.95, 0.93, 0.92, 0.9, 0.88, 0.86, 0.84, 0.82, 0.78, 0.72, 0.62]) for s in studs}
    start = date.today() - timedelta(weeks=weeks)
    n_sessions = 0
    for ci, c in enumerate(courses):
        for w in range(weeks):
            for day in (ci % 3, ci % 3 + 2):  # two lectures a week
                d = start + timedelta(weeks=w, days=day)
                if d >= date.today():
                    continue
                t0 = datetime.combine(d, datetime.min.time()) + timedelta(hours=9 + ci)
                sess = ClassSession(course=c, date=d, started_at=t0, ended_at=t0 + timedelta(minutes=55),
                                    topic=rng.choice(TOPICS), created_by=c.faculty.id)
                db.session.add(sess)
                n_sessions += 1
                for s in studs:
                    r = rng.random()
                    p = tendency[s.id]
                    status = "present" if r < p - 0.06 else "late" if r < p else "absent"
                    method = "face" if status != "absent" and rng.random() < 0.9 else ("manual" if status != "absent" else "auto")
                    mins = rng.randint(1, 8) if status == "present" else rng.randint(11, 25)
                    db.session.add(Attendance(session=sess, student=s, status=status, method=method,
                                              confidence=round(rng.uniform(0.55, 0.85), 3) if method == "face" else None,
                                              marked_at=t0 + timedelta(minutes=mins) if status != "absent" else sess.ended_at))
    db.session.commit()
    return [
        f"{len(studs)} students, {len(courses)} courses, {n_sessions} past sessions",
        "admin@demo.local / admin123",
        "faculty1@demo.local / faculty123  (also faculty2, faculty3)",
        "student@demo.local / student123",
    ]
