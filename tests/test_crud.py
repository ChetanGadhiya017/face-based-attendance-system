import io

from attendance.extensions import db
from attendance.models import Enrollment, Student


def test_create_student_and_duplicate(admin, app):
    r = admin.post("/students/new", data={"roll_no": "23bcp099", "name": "  New   Person ", "year": 2})
    assert r.status_code == 302
    with app.app_context():
        st = Student.query.filter_by(roll_no="23BCP099").one()
        assert st.name == "New Person"
    r = admin.post("/students/new", data={"roll_no": "23BCP099", "name": "Dup"})
    assert b"already belongs" in r.data


def test_edit_and_delete_student(admin, app):
    admin.post("/students/1/edit", data={"roll_no": "23BCP001", "name": "Renamed", "year": 3})
    with app.app_context():
        assert db.session.get(Student, 1).name == "Renamed"
    admin.post("/students/1/delete")
    with app.app_context():
        assert db.session.get(Student, 1) is None


def test_search_and_filters(admin):
    r = admin.get("/students?q=Student 2")
    assert b"23BCP002" in r.data and b"23BCP003" not in r.data
    assert b"23BCP001" in admin.get("/students?face=no").data


def test_csv_import(admin, app):
    csv = ("roll_no,name,email,department,year,division\n23BCP050,Imported One,a@b.c,ECE,2,D2\n"
           "23BCP001,Updated Name,,CSE,3,D1\n,Missing,,,,\n")
    r = admin.post("/students/import", data={"file": (io.BytesIO(csv.encode()), "s.csv")}, content_type="multipart/form-data")
    assert r.status_code == 302
    with app.app_context():
        assert Student.query.filter_by(roll_no="23BCP050").one().department.code == "ECE"
        assert Student.query.filter_by(roll_no="23BCP001").one().name == "Updated Name"
    assert admin.get("/students/template.csv").data.startswith(b"roll_no,name")


def test_course_crud_and_enrollment(admin, app):
    r = admin.post("/courses/new", data={"code": "cs200", "name": "Compilers"})
    assert r.status_code == 302
    cid = int(r.headers["Location"].rsplit("/", 1)[1])
    admin.post(f"/courses/{cid}/enroll", data={"mode": "division", "division": "D1"})
    with app.app_context():
        assert Enrollment.query.filter_by(course_id=cid).count() == 4
    admin.post(f"/courses/{cid}/unenroll/1")
    admin.post(f"/courses/{cid}/enroll", data={"mode": "rolls", "rolls": "23bcp001, nope"})
    with app.app_context():
        assert Enrollment.query.filter_by(course_id=cid).count() == 4
    assert b"already exists" in admin.post("/courses/new", data={"code": "CS200", "name": "Again"}).data
    admin.post(f"/courses/{cid}/delete")
    assert admin.get(f"/courses/{cid}").status_code == 404


def test_pages_render(admin):
    for url in ("/dashboard", "/students", "/students/1", "/courses", "/courses/1", "/reports", "/users", "/students/import"):
        assert admin.get(url).status_code == 200, url
