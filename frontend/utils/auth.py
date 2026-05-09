"""
Authentication utilities — password hashing and session helpers.
Uses hashlib (stdlib) with SHA-256 + random salt; no extra dependencies.
"""
import hashlib
import os
import random
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText

import streamlit as st

from frontend.utils import db


def _hash_password(password: str, salt: str) -> str:
    return hashlib.sha256((salt + password).encode()).hexdigest()


def hash_password(password: str) -> str:
    """Return 'salt:hash' string for storage."""
    salt = os.urandom(16).hex()
    return f"{salt}:{_hash_password(password, salt)}"


def verify_password(password: str, stored: str) -> bool:
    """Verify a plaintext password against a stored 'salt:hash'."""
    try:
        salt, hsh = stored.split(":", 1)
        return _hash_password(password, salt) == hsh
    except Exception:
        return False


def register(username: str, email: str, password: str, role: str,
             shelter_name: str | None = None) -> tuple[bool, str]:
    """
    Register a new user.
    Returns (success, message).
    """
    if len(password) < 6:
        return False, "Password must be at least 6 characters."
    if not username.strip():
        return False, "Username cannot be empty."
    if not email.strip() or "@" not in email:
        return False, "Please enter a valid email address."
    pw_hash = hash_password(password)
    uid = db.create_user(username.strip(), email.strip(), pw_hash, role,
                         shelter_name=shelter_name)
    if uid is None:
        return False, "Username or email already exists."
    return True, "Account created successfully."


def login(username: str, password: str) -> tuple[bool, str]:
    """
    Authenticate user. On success stores user dict in st.session_state.user.
    Returns (success, message).
    """
    user = db.get_user_by_username(username.strip())
    if not user:
        return False, "Invalid username or password."
    if not verify_password(password, user["password_hash"]):
        return False, "Invalid username or password."
    st.session_state.user = dict(user)
    return True, f"Welcome back, {user['username']}!"


def verify_credentials(username: str, password: str) -> "dict | None":
    """Verify credentials and return user dict without touching session state."""
    user = db.get_user_by_username(username.strip())
    if not user or not verify_password(password, user["password_hash"]):
        return None
    return dict(user)


def logout():
    st.session_state.pop("user", None)
    for key in ["mp_view", "mp_listing_id", "mp_chat_with", "mp_chat_listing",
                "_2fa_pending_user", "_2fa_code", "_2fa_expiry"]:
        st.session_state.pop(key, None)


def current_user() -> "dict | None":
    return st.session_state.get("user")


def is_shelter_manager() -> bool:
    u = current_user()
    return u is not None and u.get("role") == "shelter_manager"


def is_household() -> bool:
    u = current_user()
    return u is not None and u.get("role") == "household"


def is_admin() -> bool:
    u = current_user()
    return u is not None and u.get("role") == "admin"


def change_password(user_id: int, current_pw: str, new_pw: str) -> "tuple[bool, str]":
    user = db.get_user_by_id(user_id)
    if not user:
        return False, "User not found."
    if not verify_password(current_pw, user["password_hash"]):
        return False, "Current password is incorrect."
    if len(new_pw) < 6:
        return False, "New password must be at least 6 characters."
    new_hash = hash_password(new_pw)
    db.update_user(user_id, password_hash=new_hash)
    return True, "Password changed successfully."


def send_2fa_code(email: str) -> "tuple[bool, str]":
    """Send a 6-digit 2FA code to the given email via SMTP from secrets.toml.
    Returns (True, code) on success, (False, reason) on failure."""
    try:
        smtp_conf = st.secrets.get("smtp", {})
        if not smtp_conf or not smtp_conf.get("host"):
            return False, "no_smtp"
        code = f"{random.randint(0, 999999):06d}"
        msg = MIMEText(
            f"Your AdoptSense admin verification code: {code}\n\n"
            f"This code expires in 10 minutes. Do not share it."
        )
        msg["Subject"] = "AdoptSense Admin Login Code"
        msg["From"] = smtp_conf["user"]
        msg["To"] = email
        with smtplib.SMTP(smtp_conf["host"], int(smtp_conf.get("port", 587))) as s:
            s.ehlo()
            s.starttls()
            s.login(smtp_conf["user"], smtp_conf["password"])
            s.send_message(msg)
        return True, code
    except Exception as exc:
        return False, str(exc)


def require_login(action: str = "use this feature") -> bool:
    """Show a prompt to log in if the user is not authenticated.
    Returns True if logged in, False otherwise."""
    if current_user():
        return True
    st.warning(f"Please **log in** or **register** to {action}.")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔑 Log In", use_container_width=True):
            st.session_state.show_auth = "login"
            st.rerun()
    with col2:
        if st.button("📝 Register", use_container_width=True):
            st.session_state.show_auth = "register"
            st.rerun()
    return False
