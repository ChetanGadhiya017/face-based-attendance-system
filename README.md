<div align="center">

# 🙂 FaceAttend: Face Recognition Attendance System

**Attendance that takes itself.** Students look at a webcam and are marked present in under a second. Late arrivals are flagged automatically, and anyone missing is marked absent when the lecture ends.

A full-stack web app built on a normalised university database (originally a DBMS course project), with role-based access, live dashboards and exportable registers.

[![CI](https://github.com/ChetanGadhiya017/face-based-attendance-system/actions/workflows/ci.yml/badge.svg)](https://github.com/ChetanGadhiya017/face-based-attendance-system/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3-000000?logo=flask)
![OpenCV](https://img.shields.io/badge/OpenCV-YuNet%20%2B%20SFace-5C3EE8?logo=opencv&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-SQLite%20%7C%20MySQL-D71F00)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)
![Tests](https://img.shields.io/badge/tests-29%20passing-brightgreen)

<img src="docs/screenshots/dashboard.png" alt="Dashboard" width="92%" />

</div>

---

## ✨ Features

### For faculty
- 🎥 **Live attendance in the browser**: open a session, press *Start camera*. Every recognised face gets a box and a name and is marked in real time (about 150 ms per frame)
- ⏱️ **Late detection**: arrivals after a configurable number of minutes are marked *late*
- ✋ **One-click corrections**: Present / Late / Absent for anyone, before or after closing
- 🔒 **Close session**: everyone not yet marked becomes *absent* automatically
- 📈 **Reports**: per-course register, the *sessions needed to get back to 75%* for each student, a per-session chart and a full CSV register (P/L/A matrix)

### For administrators
- 🎓 **Students**: search, filters, pagination, CSV import (with template), profiles with per-course attendance
- 📷 **Face enrolment** from the webcam or uploaded photos. A sample is rejected if it has no face or several faces, or if the face matches *another* student (wrong person selected)
- 📚 **Courses**: assign faculty, bulk-enrol by division, department or roll numbers
- 🔑 **Users & roles**: admin, faculty (sees only their own courses), student

### For students
- 🗓️ **My attendance** portal: percentage per course, warnings below the minimum, recent history

### Under the hood
- 🧠 **OpenCV YuNet + SFace** (detection + 128-d embeddings). No dlib, so `pip install` works on Windows without compilers
- 🎯 Matching needs a similarity threshold **and** a margin over the runner-up, so look-alike classmates are not confused
- 🛡️ Stores face **embeddings and a 96 px thumbnail only**, never full photos
- 🔐 CSRF protection, hashed passwords, role checks on every route, secure cookies, safe redirects, security headers
- 🌗 Light/dark theme, responsive layout, accessible forms

<table>
<tr>
<td width="50%"><img src="docs/screenshots/live-session.png" alt="Live session" /><p align="center"><sub>Live session: camera + realtime roster</sub></p></td>
<td width="50%"><img src="docs/screenshots/reports.png" alt="Reports" /><p align="center"><sub>Reports: who needs how many sessions to reach 75%</sub></p></td>
</tr>
<tr>
<td width="50%"><img src="docs/screenshots/dashboard-dark.png" alt="Dark mode" /><p align="center"><sub>Dark mode</sub></p></td>
<td width="50%"><img src="docs/screenshots/login.png" alt="Sign in" /><p align="center"><sub>Sign in</sub></p></td>
</tr>
</table>

---

## 🚀 Quick start

```bash
git clone https://github.com/ChetanGadhiya017/face-based-attendance-system.git
cd face-based-attendance-system
python -m venv .venv && .venv\Scripts\activate        # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

flask --app wsgi download-models     # YuNet + SFace (~38 MB, verified by SHA-256)
flask --app wsgi seed-demo           # optional: 48 synthetic students, 4 courses, 6 weeks of history
flask --app wsgi run                 # → http://127.0.0.1:5000
```

| Demo account | Password | Can do |
|---|---|---|
| `admin@demo.local` | `admin123` | everything |
| `faculty1@demo.local` | `faculty123` | their courses, sessions, reports |
| `student@demo.local` | `student123` | own attendance only |

For real use, skip `seed-demo` and create your admin with `flask --app wsgi create-admin`.

> The camera needs a secure context: `localhost` works out of the box. On another machine, serve over **HTTPS**.

### Docker

```bash
docker compose up --build          # web app + MySQL 8 → http://localhost:8000
docker compose exec web flask --app wsgi create-admin
```

### Configuration (`.env`)

| Variable | Default | Meaning |
|---|---|---|
| `SECRET_KEY` | dev value | Session signing key. **Set this in production** |
| `DATABASE_URL` | SQLite in `instance/` | e.g. `mysql+pymysql://user:pass@host/db` |
| `RECOGNITION_THRESHOLD` | `0.42` | Minimum cosine similarity for a match |
| `RECOGNITION_MARGIN` | `0.05` | Required lead over the second-best student |
| `LATE_AFTER_MINUTES` | `10` | Minutes after start before arrivals count as late |
| `MIN_ATTENDANCE_PERCENT` | `75` | Threshold for warnings and defaulter lists |
| `SESSION_COOKIE_SECURE` | `0` | Set `1` behind HTTPS |

---

## 🏗 Architecture

```mermaid
flowchart LR
    subgraph Browser
      CAM[Webcam] --> LJS[live.js<br/>JPEG frame ~1/s]
      UI[Jinja pages + Chart.js]
    end
    LJS -- POST /api/sessions/:id/recognize --> API
    subgraph Flask
      API[JSON API] --> SV[services.py]
      VW[views.py] --> SV
      SV --> FE[FaceEngine<br/>YuNet → SFace]
      SV --> DB[(SQLAlchemy<br/>SQLite / MySQL)]
    end
    FE -- 128-d embedding --> M{best match<br/>threshold + margin}
    M -->|enrolled student| DB
```

**Recognition pipeline:** YuNet finds faces and 5 landmarks → SFace aligns each face and produces a 128-d embedding → cosine similarity against every enrolled student's samples → match only if above the threshold *and* ahead of the runner-up → mark *present* or *late* once per session.

### Data model

```mermaid
erDiagram
    DEPARTMENT ||--o{ STUDENT : has
    DEPARTMENT ||--o{ COURSE : offers
    USER ||--o{ COURSE : teaches
    USER |o--o| STUDENT : "portal login"
    STUDENT ||--o{ FACE_SAMPLE : "enrolled with"
    STUDENT ||--o{ ENROLLMENT : takes
    COURSE ||--o{ ENROLLMENT : has
    COURSE ||--o{ CLASS_SESSION : holds
    CLASS_SESSION ||--o{ ATTENDANCE : records
    STUDENT ||--o{ ATTENDANCE : has
    ATTENDANCE {
      string status "present | late | absent"
      string method "face | manual | auto"
      float confidence
      datetime marked_at
    }
```

The original DBMS-course design (10-table MySQL schema with schools, programs, divisions and groups, plus ER models and sample queries) is preserved in [`docs/dbms`](docs/dbms).

```
attendance/
├── __init__.py      app factory, security headers
├── models.py        SQLAlchemy models + attendance statistics query
├── face.py          FaceEngine (YuNet + SFace), model download, matching
├── services.py      enrol faces, sessions, marking, frame recognition
├── views.py         pages (dashboard, students, courses, sessions, reports, portal, users)
├── api.py           JSON endpoints for the camera pages
├── auth.py          login / logout / password
├── cli.py           init-db · create-admin · download-models · seed-demo
├── templates/       Jinja templates
└── static/          CSS design system, live.js, enroll.js, charts.js
tests/               29 tests (fake face engine + real-model checks)
```

---

## 🧪 Tests

```bash
pip install pytest
pytest -q
```

They cover authentication and open-redirect protection, role scoping, student/course CRUD and CSV import, face enrolment rules, the live recognition flow (marked / already / unknown, late detection), manual corrections, auto-absent on close, reports and CSV exports, and the matching margin. CI also builds the Docker image and smoke-tests it.

---

## 🔐 Privacy

- Only embeddings (128 numbers) and a small thumbnail are stored per sample; frames from the camera are processed in memory and discarded.
- Deleting a student deletes their samples and records.
- The demo data is entirely synthetic.

## 🤝 Contributors

<table>
  <tr>
    <td align="center"><a href="https://github.com/ChetanGadhiya017"><img src="https://github.com/ChetanGadhiya017.png" width="80" alt=""/><br/><sub><b>Chetan Gadhiya</b></sub></a></td>
    <td align="center"><a href="https://github.com/VedeshP"><img src="https://github.com/VedeshP.png" width="80" alt=""/><br/><sub><b>Vedesh Pandya</b></sub></a></td>
  </tr>
</table>
