from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_login_page_renders():
    app = Path(__file__).resolve().parents[1] / "app.py"
    result = AppTest.from_file(str(app)).run(timeout=30)
    assert not result.exception
    assert any("Sign in" in item.value for item in result.markdown)


def test_operator_can_login_to_refinery():
    app = Path(__file__).resolve().parents[1] / "app.py"
    result = AppTest.from_file(str(app)).run(timeout=30)
    result.text_input[0].set_value("operator")
    result.text_input[1].set_value("Operator@123")
    result.selectbox[0].select("refinery")
    result.button[0].click().run(timeout=30)
    assert not result.exception
    assert any("Butamer Unit Overview" in item.value for item in result.markdown)
