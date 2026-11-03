from __future__ import annotations

import hashlib
import hmac
import os
from dataclasses import dataclass

import streamlit as st


@dataclass(frozen=True)
class User:
    username: str
    display_name: str
    role: str


_DEFAULT_HASHES = {
    "operator": "448296e3138d4843057574ba9fbd21829f1f6d40891ce89664608ce55005a7ef",
    "admin": "e86f78a8a3caf0b60d8e74e5942aa6d86dc150cd3c03338aef25b7d2d7e3acc7",
}


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _expected_hash(username: str) -> str:
    env_name = f"PORTAL_{username.upper()}_PASSWORD"
    if os.getenv(env_name):
        return _digest(os.environ[env_name])
    try:
        configured = st.secrets.get("auth", {}).get(f"{username}_password", "")
    except Exception:
        configured = ""
    return _digest(str(configured)) if configured else _DEFAULT_HASHES[username]


def authenticate(username: str, password: str) -> User | None:
    key = username.strip().lower()
    if key not in _DEFAULT_HASHES:
        return None
    if not hmac.compare_digest(_digest(password), _expected_hash(key)):
        return None
    if key == "admin":
        return User("admin", "Portal Administrator", "admin")
    return User("operator", "Operations User", "operator")


def initialise_session() -> None:
    defaults = {
        "authenticated": False,
        "username": "",
        "display_name": "",
        "role": "",
        "business_unit": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def sign_in(user: User, business_unit: str) -> None:
    st.session_state.authenticated = True
    st.session_state.username = user.username
    st.session_state.display_name = user.display_name
    st.session_state.role = user.role
    st.session_state.business_unit = business_unit


def sign_out() -> None:
    for key in ("authenticated", "username", "display_name", "role", "business_unit"):
        st.session_state.pop(key, None)
    st.rerun()
