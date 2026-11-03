from __future__ import annotations

import streamlit as st

from portal import auth, config_store, db, pages, ui

st.set_page_config(
    page_title="Digital Operations & Knowledge Portal",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

ui.inject_styles()
auth.initialise_session()
db.init_db()

try:
    BUSINESS_UNITS = config_store.load_business_units()
except config_store.ConfigError as exc:
    st.error(str(exc))
    st.stop()


def render_login() -> None:
    st.markdown('<div class="login-wrap">', unsafe_allow_html=True)
    brand, panel = st.columns([1.08, .92], gap="large")
    with brand:
        st.markdown(
            """
<div class="login-brand">
  <div>
    <span class="portal-chip">DIGITAL OPERATIONS</span>
    <h1>One portal.<br>Different businesses.<br>Shared control.</h1>
    <p>Operational monitoring, digital rounds, process analytics, SOP knowledge, event history and administration in one configurable Streamlit application.</p>
  </div>
  <div>
    <strong>Designed for replication</strong><br>
    <span style="opacity:.82">Business-unit structure, page labels, KPIs, rounds and source data are configuration-driven.</span>
  </div>
</div>
""",
            unsafe_allow_html=True,
        )
    with panel:
        st.markdown('<div class="login-panel">', unsafe_allow_html=True)
        st.markdown("### Sign in to your workspace")
        st.caption("Enter your credentials, then choose the business unit you want to open.")
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Your portal username")
            password = st.text_input("Password", type="password", placeholder="Your password")
            business_unit = st.selectbox(
                "Business unit",
                options=list(BUSINESS_UNITS),
                format_func=lambda key: BUSINESS_UNITS[key]["name"],
                help="Your selection determines the workspace, hierarchy, KPIs, round forms and knowledge area shown after sign-in.",
            )
            submitted = st.form_submit_button("Log in", type="primary", use_container_width=True)
        if submitted:
            user = auth.authenticate(username, password)
            if user is None:
                st.error("The username or password is not valid.")
                db.log_action(username or "unknown", "unknown", business_unit, "login_failed")
            else:
                auth.sign_in(user, business_unit)
                db.log_action(user.username, user.role, business_unit, "login_success")
                st.rerun()
        with st.expander("First-run demonstration credentials"):
            st.code("Operator: operator / Operator@123\nAdministrator: admin / Admin@123")
            st.warning("Change both passwords through environment variables or Streamlit secrets before a real deployment.")
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


if not st.session_state.authenticated:
    render_login()
    st.stop()

slug = st.session_state.business_unit
if slug not in BUSINESS_UNITS:
    auth.sign_out()
    st.stop()
config = BUSINESS_UNITS[slug]
navigation = config.get("navigation", {})
labels = {
    "Home": navigation.get("overview", "Operations Center"),
    "Analytics": navigation.get("analytics", "Operations Analytics"),
    "Digital rounds": navigation.get("rounds", "Digital Operator Rounds"),
    "SOP & knowledge": navigation.get("sops", "SOP & Knowledge"),
    "Events": navigation.get("events", "Events & Investigations"),
    "Admin": navigation.get("admin", "Administration"),
}
features = set(config.get("features", ["Home", "Analytics", "Digital rounds", "SOP & knowledge", "Events"]))
routes = [route for route in ["Home", "Analytics", "Digital rounds", "SOP & knowledge", "Events"] if route in features]
if st.session_state.role == "admin":
    routes.append("Admin")

with st.sidebar:
    st.markdown("## Digital Operations")
    st.caption(" &nbsp;›&nbsp; ".join(config.get("hierarchy", [])), unsafe_allow_html=True)
    st.divider()
    selected_page = st.radio("Workspace", routes, format_func=lambda route: labels[route], label_visibility="collapsed")
    st.divider()
    st.markdown(f"**{st.session_state.display_name}**")
    st.caption(f"Role: {st.session_state.role.title()}")
    st.caption(f"Business unit: {config['name']}")
    if st.button("Sign out"):
        db.log_action(st.session_state.username, st.session_state.role, slug, "logout")
        auth.sign_out()

pages.render_page(selected_page, slug, config, BUSINESS_UNITS)
