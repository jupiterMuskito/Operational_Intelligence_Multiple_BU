from __future__ import annotations

import html
from typing import Any

import streamlit as st

BLUE = "#1857C9"
BLUE_DARK = "#0F3F9C"
RED = "#C6303E"
INK = "#14202E"
MUTED = "#5C7086"


def inject_styles() -> None:
    st.markdown(
        f"""
<style>
:root{{--portal-blue:{BLUE};--portal-dark:{BLUE_DARK};--portal-red:{RED};--portal-ink:{INK};}}
.stApp{{background:#f3f6fb;color:{INK}}}
[data-testid="stHeader"]{{background:rgba(243,246,251,.88)}}
[data-testid="stSidebar"]{{background:#0f2f5f;border-right:0}}
[data-testid="stSidebar"] *{{color:#f6f9ff}}
[data-testid="stSidebar"] [data-baseweb="select"] *{{color:#14202e}}
[data-testid="stSidebar"] .stButton button{{width:100%;background:transparent;color:white;border:1px solid rgba(255,255,255,.35)}}
.portal-hero{{position:relative;overflow:hidden;background:linear-gradient(120deg,#0c2f63 0%,#1857c9 68%,#2f7de1 100%);color:white;padding:1.45rem 1.6rem;border-radius:16px;margin:.15rem 0 1.1rem;box-shadow:0 12px 30px rgba(15,63,156,.18)}}
.portal-hero:after{{content:"";position:absolute;width:240px;height:240px;border:34px solid rgba(255,255,255,.08);border-radius:50%;right:-80px;top:-105px}}
.portal-hero h1{{font-size:2rem;margin:0 0 .3rem;line-height:1.12}}
.portal-hero p{{margin:0;opacity:.9;max-width:850px}}
.portal-crumb{{font-size:.78rem;text-transform:uppercase;letter-spacing:.09em;opacity:.76;margin-bottom:.55rem}}
.portal-card{{background:white;border:1px solid #d7e3ee;border-radius:13px;padding:1rem 1.05rem;height:100%;box-shadow:0 3px 10px rgba(20,32,46,.035)}}
.portal-card h3{{margin:.15rem 0 .35rem;font-size:1.02rem}}
.portal-card p{{margin:0;color:{MUTED};font-size:.9rem}}
.portal-chip{{display:inline-block;padding:.22rem .58rem;border-radius:999px;background:#e4eefb;color:{BLUE_DARK};font-size:.76rem;font-weight:700}}
.portal-chip.demo{{background:#fff1d6;color:#7d5200}}
.portal-chip.live{{background:#e2f5e8;color:#216b38}}
div[data-testid="stMetric"]{{background:#fff;border:1px solid #d7e3ee;padding:.85rem 1rem;border-radius:12px;box-shadow:0 3px 10px rgba(20,32,46,.03)}}
.stButton>button,.stDownloadButton>button{{border-radius:8px;border:1px solid {BLUE}}}
.stButton>button[kind="primary"]{{background:{BLUE};color:#fff}}
[data-testid="stDataFrame"]{{background:#fff;border:1px solid #d7e3ee;border-radius:10px}}
.login-wrap{{max-width:960px;margin:2.5rem auto 0}}
.login-brand{{background:linear-gradient(145deg,#0c2f63,#1857c9);color:#fff;border-radius:18px;padding:2rem;min-height:390px;display:flex;flex-direction:column;justify-content:space-between}}
.login-brand h1{{font-size:2.25rem;line-height:1.05;margin:.5rem 0}}
.login-brand p{{opacity:.88}}
.login-panel{{background:#fff;border:1px solid #d7e3ee;border-radius:18px;padding:1.6rem 1.7rem;box-shadow:0 14px 35px rgba(15,47,95,.12)}}
.small-note{{font-size:.82rem;color:{MUTED}}}
.status-ok{{color:#267348;font-weight:700}} .status-bad{{color:{RED};font-weight:700}}
.portal-table{{width:100%;border-collapse:collapse;background:#fff;border:1px solid #d7e3ee;border-radius:10px;overflow:hidden;font-size:.88rem}}
.portal-table th{{background:#edf3fb;color:#0f3f9c;text-align:left;padding:.6rem;border-bottom:1px solid #d7e3ee}}
.portal-table td{{padding:.58rem;border-bottom:1px solid #edf1f6}}
</style>
""",
        unsafe_allow_html=True,
    )


def hero(config: dict[str, Any], title: str, subtitle: str) -> None:
    hierarchy = " &nbsp;›&nbsp; ".join(html.escape(str(x)) for x in config.get("hierarchy", []))
    st.markdown(
        f'<div class="portal-hero"><div class="portal-crumb">{hierarchy}</div>'
        f'<h1>{html.escape(title)}</h1><p>{html.escape(subtitle)}</p></div>',
        unsafe_allow_html=True,
    )


def card(title: str, text: str, badge: str = "") -> str:
    badge_html = f'<span class="portal-chip">{html.escape(badge)}</span>' if badge else ""
    return f'<div class="portal-card">{badge_html}<h3>{html.escape(title)}</h3><p>{html.escape(text)}</p></div>'


def fmt_number(value: Any, decimals: int = 1) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "—"
    if abs(number) >= 1_000_000:
        return f"{number / 1_000_000:,.2f}M"
    if abs(number) >= 1_000:
        return f"{number:,.0f}"
    return f"{number:,.{decimals}f}"
