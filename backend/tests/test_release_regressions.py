from backend.routers import auth
from backend.services.easm_engine import _make_alert_id
from backend.services.ids_engine import _ai_triage_enabled


def test_failed_login_lockout_is_scoped_to_account_and_client():
    auth._LOGIN_ATTEMPTS.clear()
    admin_key = ("192.0.2.10", "admin")
    student_key = ("192.0.2.10", "student")

    for _ in range(auth._MAX_ATTEMPTS):
        auth._record_failed_attempt(admin_key)

    assert auth._check_rate_limit(admin_key) == (False, 0)
    assert auth._check_rate_limit(student_key) == (True, auth._MAX_ATTEMPTS)

    auth._clear_attempts(admin_key)
    assert auth._check_rate_limit(admin_key) == (True, auth._MAX_ATTEMPTS)


def test_easm_alert_ids_fit_database_column_and_include_subject_hash():
    first = _make_alert_id(
        "easm_shadow",
        "dev-vpn-test.netrunner-corp.internal",
        timestamp=1_700_000_000,
    )
    second = _make_alert_id(
        "easm_shadow",
        "another.netrunner-corp.internal",
        timestamp=1_700_000_000,
    )

    assert len(first) <= 50
    assert len(second) <= 50
    assert first != second


def test_background_ai_triage_requires_explicit_opt_in(monkeypatch):
    monkeypatch.delenv("NETRUNNER_ENABLE_AI_TRIAGE", raising=False)

    assert not _ai_triage_enabled({})
    assert not _ai_triage_enabled({"enable_ai_triage": "false"})
    assert _ai_triage_enabled({"enable_ai_triage": True})
    assert _ai_triage_enabled({"enable_ai_triage": "on"})
