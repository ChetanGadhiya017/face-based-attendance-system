from conftest import login


def test_login_required(client):
    r = client.get("/dashboard")
    assert r.status_code == 302 and "/login" in r.headers["Location"]


def test_bad_login(client):
    r = login(client, "admin@x.io", "wrong")
    assert r.status_code == 200 and b"Invalid email or password" in r.data


def test_login_and_logout(client):
    assert login(client, "ADMIN@x.io", "adminpass1").status_code == 302
    assert client.get("/dashboard").status_code == 200
    client.post("/logout")
    assert client.get("/dashboard").status_code == 302


def test_open_redirect_blocked(client):
    r = client.post("/login?next=https://evil.example/", data={"email": "admin@x.io", "password": "adminpass1"})
    assert r.headers["Location"] == "/"


def test_student_only_sees_portal(client):
    login(client, "stud@x.io", "studpass1")
    assert client.get("/me").status_code == 200
    for url in ("/dashboard", "/students", "/courses", "/reports", "/users", "/sessions/1"):
        assert client.get(url).status_code in (403, 404), url


def test_faculty_scope(faculty):
    assert faculty.get("/courses/1").status_code == 200
    assert faculty.get("/courses/2").status_code == 403
    assert faculty.get("/students/new").status_code == 403
    assert faculty.get("/users").status_code == 403
    assert b"CS102" not in faculty.get("/courses").data


def test_change_password(client):
    login(client, "fac@x.io", "facpass12")
    r = client.post("/account/password", data={"current": "facpass12", "new": "newpass123", "confirm": "newpass123"})
    assert r.status_code == 302
    client.post("/logout")
    assert login(client, "fac@x.io", "newpass123").status_code == 302


def test_admin_creates_and_deactivates_user(admin, app):
    r = admin.post("/users", data={"name": "New Prof", "email": "np@x.io", "role": "faculty", "password": "longenough"})
    assert r.status_code == 302
    from attendance.models import User

    with app.app_context():
        u = User.query.filter_by(email="np@x.io").one()
        uid = u.id
    admin.post(f"/users/{uid}/toggle")
    admin.post("/logout")
    assert b"Invalid" in login(admin, "np@x.io", "longenough").data


def test_security_headers(client):
    r = client.get("/login")
    assert r.headers["X-Frame-Options"] == "DENY" and "camera=(self)" in r.headers["Permissions-Policy"]
