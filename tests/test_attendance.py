from datetime import timedelta

import numpy as np
import pytest
from conftest import person_image

from attendance.extensions import db
from attendance.face import best_match
from attendance.models import Attendance, ClassSession, attendance_stats


def start(client, cid=1):
    r = client.post(f"/courses/{cid}/sessions", data={"topic": "Graphs"})
    return int(r.headers["Location"].rsplit("/", 1)[1])


def enroll(client, sid, person):
    return client.post(f"/api/students/{sid}/faces", json={"image": person_image(person)})


def test_face_enrolment_rules(faculty):
    r = enroll(faculty, 1, 1)
    assert r.status_code == 201 and r.get_json()["count"] == 1
    assert enroll(faculty, 1, 1).status_code == 201  # second sample of the same person is fine
    r = enroll(faculty, 2, 1)  # same face for another student → rejected
    assert r.status_code == 422 and "looks like Student 1" in r.get_json()["error"]
    r = faculty.post("/api/students/2/faces", json={"image": person_image(2, 3)})
    assert r.status_code == 422 and "More than one face" in r.get_json()["error"]
    assert faculty.post("/api/students/2/faces", json={"image": person_image()}).status_code == 422
    assert faculty.post("/api/students/2/faces", json={}).status_code == 422


def test_delete_face(faculty, app):
    fid = enroll(faculty, 1, 1).get_json()["id"]
    assert faculty.delete(f"/api/students/2/faces/{fid}").status_code == 404
    assert faculty.delete(f"/api/students/1/faces/{fid}").get_json()["ok"]


def test_live_recognition_flow(faculty, app):
    enroll(faculty, 1, 1)
    enroll(faculty, 2, 2)
    enroll(faculty, 4, 4)  # student 4 is NOT enrolled in CS101
    sid = start(faculty)
    body = faculty.post(f"/api/sessions/{sid}/recognize", json={"image": person_image(1, 2, 4, 9)}).get_json()
    statuses = [f["status"] for f in body["faces"]]
    assert statuses == ["marked", "marked", "unknown", "unknown"]
    assert body["faces"][0]["marked_as"] == "present" and body["summary"]["present"] == 2
    again = faculty.post(f"/api/sessions/{sid}/recognize", json={"image": person_image(1)}).get_json()
    assert again["faces"][0]["status"] == "already"
    roster = faculty.get(f"/api/sessions/{sid}/roster").get_json()
    got = {s["roll_no"]: s["status"] for s in roster["students"]}
    assert got == {"23BCP001": "present", "23BCP002": "present", "23BCP003": None}


def test_late_marking(faculty, app):
    enroll(faculty, 1, 1)
    sid = start(faculty)
    with app.app_context():
        s = db.session.get(ClassSession, sid)
        s.started_at -= timedelta(minutes=30)
        db.session.commit()
    body = faculty.post(f"/api/sessions/{sid}/recognize", json={"image": person_image(1)}).get_json()
    assert body["faces"][0]["marked_as"] == "late"


def test_manual_mark_close_and_export(faculty, app):
    sid = start(faculty)
    assert start(faculty) == sid  # starting again resumes the open session
    r = faculty.post(f"/api/sessions/{sid}/mark", json={"student_id": 2, "status": "late"})
    assert r.get_json()["summary"]["late"] == 1
    assert faculty.post(f"/api/sessions/{sid}/mark", json={"student_id": 4, "status": "present"}).status_code == 400
    assert faculty.post(f"/api/sessions/{sid}/mark", json={"student_id": 2, "status": "bogus"}).status_code == 400
    faculty.post(f"/sessions/{sid}/close")
    with app.app_context():
        recs = {a.student_id: (a.status, a.method) for a in Attendance.query.filter_by(session_id=sid)}
    assert recs == {1: ("absent", "auto"), 2: ("late", "manual"), 3: ("absent", "auto")}
    assert faculty.post(f"/api/sessions/{sid}/recognize", json={"image": person_image(1)}).status_code == 422
    csv = faculty.get(f"/sessions/{sid}/export.csv").data.decode()
    assert "23BCP002,Student 2,late,manual" in csv
    faculty.post(f"/sessions/{sid}/mark/1", data={"status": "present"})  # correction after closing
    with app.app_context():
        stats = {s["student_id"]: s for s in attendance_stats(course_id=1)}
    assert stats[1]["percent"] == 100.0 and stats[3]["percent"] == 0.0 and stats[2]["late"] == 1


def test_reports_and_csv(faculty):
    sid = start(faculty)
    faculty.post(f"/api/sessions/{sid}/mark", json={"student_id": 1, "status": "present"})
    faculty.post(f"/sessions/{sid}/close")
    r = faculty.get("/reports?course=1&filter=below&sort=pct")
    assert b"Student 2" in r.data and b"attend next" in r.data
    lines = faculty.get("/reports/course/1.csv").data.decode().splitlines()
    assert lines[0].startswith("roll_no,name,held,attended,late,percent,")
    assert lines[1].startswith("23BCP001,Student 1,1,1,0,100.0,P")


def test_other_faculty_cannot_touch_session(client, faculty):
    sid = start(faculty)
    faculty.post("/logout")
    client.post("/login", data={"email": "other@x.io", "password": "otherpass1"})
    assert client.get(f"/sessions/{sid}").status_code == 403
    assert client.post(f"/api/sessions/{sid}/recognize", json={"image": person_image(1)}).status_code == 403


def test_student_portal(client, faculty):
    sid = start(faculty)
    faculty.post(f"/api/sessions/{sid}/mark", json={"student_id": 1, "status": "present"})
    faculty.post(f"/sessions/{sid}/close")
    faculty.post("/logout")
    client.post("/login", data={"email": "stud@x.io", "password": "studpass1"})
    r = client.get("/me")
    assert b"Algorithms" in r.data and b"100%" in r.data


@pytest.mark.parametrize("scores, expect", [
    ({1: 0.9, 2: 0.2}, 1),     # clear winner
    ({1: 0.3, 2: 0.2}, None),  # below threshold
    ({1: 0.62, 2: 0.6}, None), # too close to runner-up
])
def test_best_match(scores, expect):
    emb = np.zeros(128, np.float32)
    emb[0] = 1
    gallery = {}
    for sid, s in scores.items():
        v = np.zeros(128, np.float32)
        v[0], v[sid] = s, np.sqrt(1 - s * s)
        gallery[sid] = v[None, :]
    assert best_match(emb, gallery, 0.42, 0.05)[0] == expect


def test_seed_demo_command(app):
    from attendance.cli import seed_demo_data

    with app.app_context():
        lines = seed_demo_data(12, 2, seed=1)
        assert "12 students" in lines[0]
        assert attendance_stats()
