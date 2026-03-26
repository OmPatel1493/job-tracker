"""
Auth endpoint integration tests — plain Python, no pytest.

Run with the backend server already started:
    cd backend
    python test_auth.py

Requires: pip install requests
"""

import sys
import time

import requests

# NOTE: routes have no /api prefix in this project (auth router prefix is /auth)
BASE = "http://localhost:8000"

TEST_EMAIL = f"testuser_{int(time.time())}@test.com"
TEST_PASSWORD = "TestPass123!"
TEST_NAME = "Test User"

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def make_request(method: str, endpoint: str, **kwargs) -> requests.Response:
    """
    Wrap requests calls and catch connection errors gracefully.
    Exits with a clear message if the server is not reachable.
    """
    url = f"{BASE}{endpoint}"
    try:
        return requests.request(method, url, timeout=10, **kwargs)
    except requests.exceptions.ConnectionError:
        print(f"ERROR: Server not running at {BASE}")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print(f"ERROR: Request timed out — {method.upper()} {url}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Result tracking
# ---------------------------------------------------------------------------

_results: list[tuple[int, str, bool, str]] = []


def check(num: int, name: str, passed: bool, detail: str = "") -> bool:
    _results.append((num, name, passed, detail))
    icon = "✅ PASS" if passed else "❌ FAIL"
    suffix = f" ({detail})" if detail else ""
    print(f"{icon} — [{num}] {name}{suffix}")
    return passed


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def run_tests():
    print()
    print("=" * 50)
    print("  Auth Endpoint Tests")
    print("=" * 50)
    print()

    access_token = ""

    # ------------------------------------------------------------------
    # 1. Health check
    # ------------------------------------------------------------------
    r = make_request("GET", "/health")
    check(
        1, "Health check",
        r.status_code == 200 and r.json().get("status") == "ok",
        f"status={r.status_code}",
    )

    # ------------------------------------------------------------------
    # 2. Register new user
    #    Returns 201 + UserResponse {id, email, full_name, is_active}
    #    (no token on register — must call /auth/login separately)
    # ------------------------------------------------------------------
    r = make_request(
        "POST", "/auth/register",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD, "full_name": TEST_NAME},
    )
    body = r.json()
    check(
        2, "Register new user",
        r.status_code == 201 and "id" in body and body.get("email") == TEST_EMAIL,
        f"status={r.status_code}, id={body.get('id')}, email={body.get('email')}",
    )

    # ------------------------------------------------------------------
    # 3. Register duplicate email → 400
    # ------------------------------------------------------------------
    r = make_request(
        "POST", "/auth/register",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD, "full_name": TEST_NAME},
    )
    check(
        3, "Register duplicate email",
        r.status_code == 400,
        f"expected 400, got {r.status_code}",
    )

    # ------------------------------------------------------------------
    # 4. Register with invalid email format → 422
    # ------------------------------------------------------------------
    r = make_request(
        "POST", "/auth/register",
        json={"email": "notanemail", "password": TEST_PASSWORD, "full_name": TEST_NAME},
    )
    check(
        4, "Register invalid email format",
        r.status_code == 422,
        f"expected 422, got {r.status_code}",
    )

    # ------------------------------------------------------------------
    # 5. Register with short password (< 8 chars) → 422
    # ------------------------------------------------------------------
    r = make_request(
        "POST", "/auth/register",
        json={"email": "short@test.com", "password": "123", "full_name": TEST_NAME},
    )
    check(
        5, "Register with short password",
        r.status_code == 422,
        f"expected 422, got {r.status_code}",
    )

    # ------------------------------------------------------------------
    # 6. Login with correct credentials → 200 + access_token
    # ------------------------------------------------------------------
    r = make_request(
        "POST", "/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
    )
    body = r.json()
    ok = r.status_code == 200 and "access_token" in body
    if ok:
        access_token = body["access_token"]
    check(
        6, "Login with correct credentials",
        ok,
        f"status={r.status_code}, token={'yes' if access_token else 'missing'}",
    )

    # ------------------------------------------------------------------
    # 7. Login with wrong password → 401
    # ------------------------------------------------------------------
    r = make_request(
        "POST", "/auth/login",
        json={"email": TEST_EMAIL, "password": "WrongPassword!"},
    )
    check(
        7, "Login with wrong password",
        r.status_code == 401,
        f"expected 401, got {r.status_code}",
    )

    # ------------------------------------------------------------------
    # 8. Login with non-existent email → 401
    # ------------------------------------------------------------------
    r = make_request(
        "POST", "/auth/login",
        json={"email": "nobody@test.com", "password": TEST_PASSWORD},
    )
    check(
        8, "Login with non-existent email",
        r.status_code == 401,
        f"expected 401, got {r.status_code}",
    )

    # ------------------------------------------------------------------
    # 9. GET /auth/me with valid token → 200, email matches, id is int
    # ------------------------------------------------------------------
    if access_token:
        r = make_request(
            "GET", "/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        body = r.json()
        email_ok = body.get("email") == TEST_EMAIL
        id_is_int = isinstance(body.get("id"), int)
        check(
            9, "GET /auth/me with valid token",
            r.status_code == 200 and email_ok and id_is_int,
            f"status={r.status_code}, email_match={email_ok}, id={body.get('id')} (int={id_is_int})",
        )
    else:
        check(9, "GET /auth/me with valid token", False, "skipped — no token from step 6")

    # ------------------------------------------------------------------
    # 10. GET /auth/me with no token → 401
    # ------------------------------------------------------------------
    r = make_request("GET", "/auth/me")
    check(
        10, "GET /auth/me with no token",
        r.status_code == 401,
        f"expected 401, got {r.status_code}",
    )

    # ------------------------------------------------------------------
    # 11. GET /auth/me with fake token → 401
    # ------------------------------------------------------------------
    r = make_request(
        "GET", "/auth/me",
        headers={"Authorization": "Bearer faketoken123"},
    )
    check(
        11, "GET /auth/me with fake token",
        r.status_code == 401,
        f"expected 401, got {r.status_code}",
    )

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    passed = sum(1 for _, _, ok, _ in _results if ok)
    total = len(_results)
    print()
    print("=" * 42)
    print(f"Auth Tests: {passed}/{total} passed")
    print("=" * 42)
    print()


if __name__ == "__main__":
    run_tests()
