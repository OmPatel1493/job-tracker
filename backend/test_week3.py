"""
Week 3 integration test — full end-to-end flow against the running API.

Run from backend/ with the server already started:
    python test_week3.py

Requires no pytest. Uses only stdlib + requests.
Install requests if needed: pip install requests
"""

import time
import uuid

import requests

BASE = "http://localhost:8000"

# ---------------------------------------------------------------------------
# Fake resume and JD text
# ---------------------------------------------------------------------------

RESUME_TEXT = """
Jane Smith
Software Engineer | jane.smith@email.com | github.com/janesmith

SUMMARY
Experienced software engineer with 4 years building scalable web APIs and
data pipelines. Passionate about clean architecture and developer tooling.

SKILLS
Languages: Python, JavaScript, TypeScript, SQL
Frameworks: FastAPI, React, Node.js, Express
Tools: Docker, Git, GitHub Actions, Postman
Cloud: AWS (EC2, S3, Lambda), Google Cloud Platform
Databases: PostgreSQL, MySQL, Redis
Other: REST APIs, CI/CD, Agile, code review

EXPERIENCE
Software Engineer — Acme Corp (2021–present)
  - Built FastAPI microservices handling 50k requests/day
  - Designed PostgreSQL schemas and wrote Alembic migrations
  - Containerised services with Docker and deployed to AWS EC2
  - Reduced CI pipeline time by 40% using GitHub Actions caching

Junior Developer — StartupXYZ (2020–2021)
  - Developed React dashboards consuming REST APIs
  - Wrote Python ETL scripts to process CSV data into MySQL
  - Participated in daily standups and sprint planning

EDUCATION
B.Sc. Computer Science — State University (2020)

PROJECTS
Job Tracker App — FastAPI + Next.js + MySQL + Pinecone
  Built an AI-powered job application tracker with resume skill extraction
  and semantic similarity scoring using Google Gemini embeddings.

Open Source Contributions — github.com/janesmith
  Contributed bug fixes and documentation to three Python libraries.
""".strip()

JD_TEXT = """
Senior Backend Engineer — TechCorp

We are looking for a Senior Backend Engineer to join our growing platform team.

REQUIREMENTS
- 3+ years of experience with Python backend development
- Strong knowledge of FastAPI or Django REST Framework
- Experience with relational databases (PostgreSQL or MySQL) and writing migrations
- Proficiency with Docker and containerised deployments
- Familiarity with cloud platforms (AWS or GCP preferred)
- Experience with REST API design and documentation
- Solid understanding of Git workflows and CI/CD pipelines

PREFERRED SKILLS
- Experience with vector databases (Pinecone, Weaviate, or similar)
- Knowledge of message queues (Redis, RabbitMQ)
- Familiarity with async Python (asyncio, SQLAlchemy async)
- React or Next.js for occasional frontend tasks

RESPONSIBILITIES
- Design and implement scalable API endpoints
- Write database migrations and maintain schema documentation
- Review pull requests and mentor junior engineers
- Collaborate with frontend and data teams

WHY JOIN US
Competitive salary, remote-first culture, and a small team where your
work has direct impact. We use modern tooling and care deeply about
code quality and developer experience.
""".strip()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

results: list[tuple[str, bool, str]] = []


def check(name: str, passed: bool, detail: str = "") -> bool:
    results.append((name, passed, detail))
    icon = "PASS" if passed else "FAIL"
    print(f"  [{icon}] {name}" + (f" — {detail}" if detail else ""))
    return passed


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def main():
    print("\n" + "=" * 60)
    print("  Week 3 Integration Test")
    print("=" * 60 + "\n")

    token = ""
    application_id = None

    # ------------------------------------------------------------------
    # Step 1 — Register a test user
    # ------------------------------------------------------------------
    print("Step 1 — Register test user")
    unique = uuid.uuid4().hex[:8]
    email = f"testuser_{unique}@example.com"
    try:
        r = requests.post(
            f"{BASE}/auth/register",
            json={"email": email, "password": "TestPass123!", "full_name": "Test User"},
            timeout=10,
        )
        check("Register user", r.status_code == 201, f"status={r.status_code}")
    except Exception as exc:
        check("Register user", False, str(exc))

    # ------------------------------------------------------------------
    # Step 2 — Login to get token
    # ------------------------------------------------------------------
    print("\nStep 2 — Login")
    try:
        r = requests.post(
            f"{BASE}/auth/login",
            data={"username": email, "password": "TestPass123!"},
            timeout=10,
        )
        ok = r.status_code == 200 and "access_token" in r.json()
        if ok:
            token = r.json()["access_token"]
        check("Login + get token", ok, f"status={r.status_code}")
    except Exception as exc:
        check("Login + get token", False, str(exc))

    if not token:
        print("\n[ABORT] Cannot continue without a token.\n")
        _print_summary()
        return

    # ------------------------------------------------------------------
    # Step 3 — Upload plain-text resume
    # ------------------------------------------------------------------
    print("\nStep 3 — Upload resume (plain text)")
    try:
        r = requests.post(
            f"{BASE}/resume/upload",
            data={"text": RESUME_TEXT},
            headers=auth_headers(token),
            timeout=30,
        )
        ok = r.status_code == 200
        check(
            "Upload resume",
            ok,
            f"status={r.status_code}" + (f", skills={list(r.json().get('parsed_skills', {}).keys())}" if ok else f", body={r.text[:120]}"),
        )
    except Exception as exc:
        check("Upload resume", False, str(exc))

    # ------------------------------------------------------------------
    # Step 4 — Create application
    # ------------------------------------------------------------------
    print("\nStep 4 — Create application")
    try:
        r = requests.post(
            f"{BASE}/applications",
            json={
                "company_name": "TechCorp",
                "job_title": "Senior Backend Engineer",
                "job_description": JD_TEXT,
                "job_url": "https://techcorp.example.com/jobs/123",
            },
            headers=auth_headers(token),
            timeout=10,
        )
        ok = r.status_code == 201
        if ok:
            application_id = r.json().get("id")
        check("Create application", ok, f"status={r.status_code}, id={application_id}")
    except Exception as exc:
        check("Create application", False, str(exc))

    if application_id is None:
        print("\n[ABORT] Cannot continue without an application ID.\n")
        _print_summary()
        return

    # ------------------------------------------------------------------
    # Step 5 — Wait for background AI pipeline
    # ------------------------------------------------------------------
    print("\nStep 5 — Wait 5 s for background AI pipeline...")
    time.sleep(5)

    # ------------------------------------------------------------------
    # Step 6 — GET application and verify fit_score
    # ------------------------------------------------------------------
    print("\nStep 6 — GET application, verify AI results")
    try:
        r = requests.get(
            f"{BASE}/applications/{application_id}",
            headers=auth_headers(token),
            timeout=10,
        )
        data = r.json()
        fit_score = data.get("fit_score")
        ok = r.status_code == 200 and fit_score is not None
        check(
            "fit_score populated",
            ok,
            f"fit_score={fit_score}, analysis_status={data.get('analysis_status')}",
        )
    except Exception as exc:
        check("fit_score populated", False, str(exc))
        data = {}

    # ------------------------------------------------------------------
    # Step 7 — Verify matched_skills and missing_skills
    # ------------------------------------------------------------------
    print("\nStep 7 — Verify matched_skills and missing_skills")
    matched = data.get("matched_skills") or []
    missing = data.get("missing_skills") or []
    check(
        "matched_skills populated",
        isinstance(matched, list) and len(matched) > 0,
        f"count={len(matched)}, sample={matched[:3]}",
    )
    check(
        "missing_skills populated",
        isinstance(missing, list) and len(missing) > 0,
        f"count={len(missing)}, sample={missing[:3]}",
    )

    # ------------------------------------------------------------------
    # Step 8 — PATCH status to "applied"
    # ------------------------------------------------------------------
    print("\nStep 8 — PATCH status to 'applied'")
    try:
        r = requests.patch(
            f"{BASE}/applications/{application_id}/status",
            json={"status": "applied", "notes": "Applied via company portal."},
            headers=auth_headers(token),
            timeout=10,
        )
        ok = r.status_code == 200 and r.json().get("status") == "applied"
        check("PATCH status to applied", ok, f"status={r.status_code}, new_status={r.json().get('status')}")
    except Exception as exc:
        check("PATCH status to applied", False, str(exc))

    # ------------------------------------------------------------------
    # Step 9 — GET stats/summary
    # ------------------------------------------------------------------
    print("\nStep 9 — GET stats/summary")
    try:
        r = requests.get(
            f"{BASE}/applications/stats/summary",
            headers=auth_headers(token),
            timeout=10,
        )
        ok = r.status_code == 200
        if ok:
            s = r.json()
            print(f"         total={s.get('total')} | by_status={s.get('by_status')} | "
                  f"avg_fit={s.get('avg_fit_score')} | highest={s.get('highest_fit_score')} | "
                  f"analyzed={s.get('analyzed_count')} | pending={s.get('pending_analysis_count')}")
        check("GET stats/summary", ok, f"status={r.status_code}")
    except Exception as exc:
        check("GET stats/summary", False, str(exc))

    # ------------------------------------------------------------------
    # Step 10 — DELETE application
    # ------------------------------------------------------------------
    print("\nStep 10 — DELETE application")
    try:
        r = requests.delete(
            f"{BASE}/applications/{application_id}",
            headers=auth_headers(token),
            timeout=10,
        )
        ok = r.status_code == 200 and r.json().get("deleted_id") == str(application_id)
        check("DELETE application", ok, f"status={r.status_code}, body={r.json()}")
    except Exception as exc:
        check("DELETE application", False, str(exc))

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    _print_summary()


def _print_summary():
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print("\n" + "=" * 60)
    print(f"  Week 3 Complete: {passed}/{total} tests passed")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
