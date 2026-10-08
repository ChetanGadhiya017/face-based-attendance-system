from __future__ import annotations

from urllib.parse import urlparse

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from .extensions import db
from .models import User, local_now

bp = Blueprint("auth", __name__)


def _safe_next(target: str | None) -> str | None:
    if target and not urlparse(target).netloc and target.startswith("/"):
        return target
    return None


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = User.query.filter_by(email=email).first()
        if user and user.is_active and user.check_password(request.form.get("password", "")):
            login_user(user, remember=bool(request.form.get("remember")))
            user.last_login = local_now()
            db.session.commit()
            return redirect(_safe_next(request.args.get("next")) or url_for("main.home"))
        flash("Invalid email or password.", "error")
    return render_template("login.html")


@bp.post("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for("auth.login"))


@bp.route("/account/password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        if not current_user.check_password(request.form.get("current", "")):
            flash("Current password is incorrect.", "error")
        elif len(request.form.get("new", "")) < 8:
            flash("New password must be at least 8 characters.", "error")
        elif request.form.get("new") != request.form.get("confirm"):
            flash("New passwords do not match.", "error")
        else:
            current_user.set_password(request.form["new"])
            db.session.commit()
            flash("Password updated.", "success")
            return redirect(url_for("main.home"))
    return render_template("password.html")
