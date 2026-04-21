"""
Seed script — populates the DB with realistic demo data.
Run from backend/:   python seed.py
"""

import asyncio
import os
import sys
from datetime import date, datetime, timedelta, timezone

# Make app importable when run from backend/
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.job_application import ApplicationStatus, JobApplication
from app.models.resume import Resume
from app.models.user import User
from app.utils.security import hash_password

# ─── Config ───────────────────────────────────────────────────────────────────

DEMO_EMAIL = "demo@jobtracker.ai"
DEMO_PASSWORD = "Demo1234!"
DEMO_FULL_NAME = "Alex Johnson"

_NOW = datetime.now(timezone.utc)


def _dt(days: int) -> datetime:
    return (_NOW - timedelta(days=days)).replace(tzinfo=None)


def _date(days: int) -> date:
    return (_NOW - timedelta(days=days)).date()


# ─── Resume data ──────────────────────────────────────────────────────────────

RESUME_TEXT = """
Alex Johnson
alex.johnson@email.com | linkedin.com/in/alexjohnson | github.com/alexjohnson

SUMMARY
Full-stack software engineer with 5+ years of experience building scalable web applications
and APIs. Passionate about clean code, performance optimization, and developer experience.

EXPERIENCE
Senior Software Engineer | TechCorp Inc. | 2021 – Present
- Built and maintained RESTful APIs using Python/FastAPI serving 2M+ requests/day
- Led migration of monolithic Django app to microservices, reducing deployment time by 60%
- Designed PostgreSQL schemas and optimized queries, improving response times by 40%
- Implemented CI/CD pipelines using GitHub Actions and Docker
- Mentored 3 junior engineers on best practices and code review

Software Engineer | StartupXYZ | 2019 – 2021
- Developed full-stack features using React, TypeScript, and Node.js
- Built data analysis dashboards consuming REST APIs with real-time metrics
- Integrated AWS services (S3, Lambda, RDS) for file storage and background processing
- Collaborated in Agile sprints: standups, retrospectives, and planning

Junior Developer | WebAgency | 2018 – 2019
- Created responsive web applications using JavaScript, HTML, and CSS
- Maintained SQL databases and wrote complex queries for reporting

EDUCATION
B.S. Computer Science | State University | 2018

SKILLS
Languages: Python, JavaScript, TypeScript, SQL, Java
Frameworks: React, FastAPI, Node.js, Django, Next.js
Tools: Docker, Git, PostgreSQL, Redis, AWS
Concepts: REST APIs, Microservices, Agile, CI/CD
Other: Machine Learning, Data Analysis

PROJECTS
JobTracker AI: Full-stack job application tracker with AI fit scoring (Python, React, PostgreSQL)
DataPipeline: ETL pipeline processing 10 GB/day using Python and PostgreSQL
""".strip()

PARSED_SKILLS = {
    "languages":  ["Python", "JavaScript", "TypeScript", "SQL", "Java"],
    "frameworks": ["React", "FastAPI", "Node.js", "Django", "Next.js"],
    "tools":      ["Docker", "Git", "PostgreSQL", "Redis", "AWS"],
    "concepts":   ["REST APIs", "Microservices", "Agile", "CI/CD"],
    "other":      ["Machine Learning", "Data Analysis"],
}

# ─── Application data ─────────────────────────────────────────────────────────

APPS = [
    dict(
        company_name="Google", job_title="Senior Software Engineer",
        status=ApplicationStatus.INTERVIEW,
        fit_score=0.82, fit_score_pct=82, fit_label="Strong Fit",
        matched_skills=["Python", "React", "Docker", "REST APIs", "PostgreSQL"],
        missing_skills=["Kubernetes", "Go", "Spanner"],
        applied_date=_date(14), created_at=_dt(15),
        notes="Had a great first interview with the team. System design round next week.",
        job_description=(
            "We are looking for a Senior Software Engineer to join our Core Infrastructure team. "
            "You will design and build distributed systems at massive scale using Python, Go, and "
            "Kubernetes. Experience with Google Cloud Platform and Spanner is a plus."
        ),
        jd_skills={"languages": ["Python", "Go"], "frameworks": [], "tools": ["Kubernetes", "GCP", "Spanner", "Docker"], "concepts": ["Distributed Systems", "REST APIs"], "other": []},
    ),
    dict(
        company_name="Meta", job_title="Full Stack Engineer",
        status=ApplicationStatus.APPLIED,
        fit_score=0.71, fit_score_pct=71, fit_label="Good Fit",
        matched_skills=["React", "JavaScript", "Node.js", "REST APIs"],
        missing_skills=["GraphQL", "Hack", "PyTorch"],
        applied_date=_date(10), created_at=_dt(11),
        notes="Applied through LinkedIn. Hoping to hear back within 2 weeks.",
        job_description=(
            "Meta is seeking a Full Stack Engineer to build the next generation of social "
            "experiences. You'll work with React, GraphQL, and Hack to create seamless "
            "user interfaces and APIs at global scale."
        ),
        jd_skills={"languages": ["JavaScript", "TypeScript", "Hack"], "frameworks": ["React", "GraphQL", "PyTorch"], "tools": [], "concepts": ["REST APIs"], "other": []},
    ),
    dict(
        company_name="Amazon", job_title="Software Development Engineer",
        status=ApplicationStatus.REJECTED,
        fit_score=0.45, fit_score_pct=45, fit_label="Moderate Fit",
        matched_skills=["Python", "AWS", "Docker"],
        missing_skills=["Scala", "Kotlin", "DynamoDB", "CDK"],
        applied_date=_date(20), created_at=_dt(21),
        notes="Got rejected after the online assessment. Need to practice more DSA.",
        job_description=(
            "Amazon is hiring an SDE to build and scale e-commerce backend systems. "
            "Strong knowledge of Kotlin or Scala, DynamoDB, and AWS CDK required. "
            "You will work on distributed systems handling millions of transactions per day."
        ),
        jd_skills={"languages": ["Java", "Kotlin", "Scala"], "frameworks": [], "tools": ["AWS", "DynamoDB", "CDK", "Docker"], "concepts": ["Distributed Systems", "Microservices"], "other": []},
    ),
    dict(
        company_name="Shopify", job_title="Backend Engineer",
        status=ApplicationStatus.OFFER,
        fit_score=0.91, fit_score_pct=91, fit_label="Excellent Fit",
        matched_skills=["Python", "Django", "PostgreSQL", "Docker", "REST APIs", "Redis"],
        missing_skills=["Ruby", "Rails"],
        applied_date=_date(30), created_at=_dt(32),
        notes="Received an offer! $185k base + equity. Decision deadline is Friday.",
        job_description=(
            "Shopify is looking for a Backend Engineer to work on our commerce platform. "
            "You'll build scalable APIs using Ruby on Rails and Python, with PostgreSQL and Redis. "
            "Experience with high-traffic web applications required."
        ),
        jd_skills={"languages": ["Python", "Ruby"], "frameworks": ["Django", "Rails"], "tools": ["PostgreSQL", "Redis", "Docker"], "concepts": ["REST APIs", "Microservices"], "other": []},
    ),
    dict(
        company_name="Stripe", job_title="ML Engineer",
        status=ApplicationStatus.PHONE_SCREEN,
        fit_score=0.67, fit_score_pct=67, fit_label="Good Fit",
        matched_skills=["Python", "Machine Learning", "FastAPI", "PostgreSQL"],
        missing_skills=["Spark", "Flink", "Scala", "MLflow"],
        applied_date=_date(7), created_at=_dt(8),
        notes="Phone screen scheduled for Thursday. Reviewing ML fundamentals.",
        job_description=(
            "Stripe is seeking an ML Engineer to build fraud detection and risk models. "
            "You'll work with Python, Spark, and Flink to process payment data at scale. "
            "Experience with MLflow and model deployment required."
        ),
        jd_skills={"languages": ["Python", "Scala"], "frameworks": ["FastAPI"], "tools": ["Spark", "Flink", "MLflow", "PostgreSQL"], "concepts": ["Machine Learning"], "other": ["Fraud Detection"]},
    ),
    dict(
        company_name="Netflix", job_title="Data Engineer",
        status=ApplicationStatus.SAVED,
        fit_score=None, fit_score_pct=None, fit_label=None,
        matched_skills=None, missing_skills=None,
        applied_date=None, created_at=_dt(2),
        notes=None,
        job_description=(
            "Netflix is hiring a Data Engineer to build and maintain our data infrastructure. "
            "You will design ETL pipelines using Spark and Kafka, and work with our "
            "petabyte-scale data warehouse to enable data-driven decisions."
        ),
        jd_skills=None,
    ),
    dict(
        company_name="Airbnb", job_title="Frontend Engineer",
        status=ApplicationStatus.REJECTED,
        fit_score=0.38, fit_score_pct=38, fit_label="Poor Fit",
        matched_skills=["JavaScript", "React", "TypeScript"],
        missing_skills=["GraphQL", "React Native", "Storybook", "Cypress"],
        applied_date=_date(25), created_at=_dt(26),
        notes="Rejected after technical screen. They wanted more mobile experience.",
        job_description=(
            "Airbnb is looking for a Frontend Engineer with deep expertise in React Native, "
            "GraphQL, and component-driven development using Storybook. "
            "You'll build cross-platform experiences for our host and guest apps."
        ),
        jd_skills={"languages": ["JavaScript", "TypeScript"], "frameworks": ["React", "React Native", "GraphQL"], "tools": ["Storybook", "Cypress"], "concepts": [], "other": []},
    ),
    dict(
        company_name="Uber", job_title="Platform Engineer",
        status=ApplicationStatus.APPLIED,
        fit_score=0.74, fit_score_pct=74, fit_label="Good Fit",
        matched_skills=["Python", "Docker", "PostgreSQL", "Microservices", "REST APIs"],
        missing_skills=["Go", "Kafka", "Presto"],
        applied_date=_date(5), created_at=_dt(6),
        notes="Applied via referral from a friend on the team.",
        job_description=(
            "Uber is hiring a Platform Engineer to build internal developer tools and "
            "infrastructure. You will work with Go, Kafka, and Presto to build "
            "high-throughput data pipelines and microservices serving millions of rides daily."
        ),
        jd_skills={"languages": ["Go", "Python"], "frameworks": [], "tools": ["Kafka", "Presto", "Docker", "PostgreSQL"], "concepts": ["Microservices", "REST APIs"], "other": []},
    ),
    dict(
        company_name="Databricks", job_title="Software Engineer - Data",
        status=ApplicationStatus.INTERVIEW,
        fit_score=0.79, fit_score_pct=79, fit_label="Strong Fit",
        matched_skills=["Python", "SQL", "Data Analysis", "Machine Learning"],
        missing_skills=["Spark", "Scala", "Delta Lake"],
        applied_date=_date(12), created_at=_dt(13),
        notes="Technical interview went well. Waiting to hear about the next round.",
        job_description=(
            "Databricks is looking for a Software Engineer to improve our Data Intelligence "
            "Platform. You'll work with Python, Scala, and Apache Spark to build Delta Lake "
            "integrations and optimize query performance at scale."
        ),
        jd_skills={"languages": ["Python", "Scala", "SQL"], "frameworks": [], "tools": ["Spark", "Delta Lake"], "concepts": ["Data Analysis", "Machine Learning"], "other": []},
    ),
    dict(
        company_name="OpenAI", job_title="Backend Engineer",
        status=ApplicationStatus.SAVED,
        fit_score=0.55, fit_score_pct=55, fit_label="Moderate Fit",
        matched_skills=["Python", "FastAPI", "PostgreSQL", "Docker"],
        missing_skills=["Kubernetes", "Rust", "CUDA", "Triton"],
        applied_date=None, created_at=_dt(1),
        notes=None,
        job_description=(
            "OpenAI is seeking a Backend Engineer to build the infrastructure powering our "
            "AI products. You will work with Python, Rust, and Kubernetes to scale APIs "
            "serving millions of users, with a focus on reliability and performance."
        ),
        jd_skills={"languages": ["Python", "Rust"], "frameworks": ["FastAPI"], "tools": ["Kubernetes", "Docker", "PostgreSQL"], "concepts": ["REST APIs", "Microservices"], "other": ["CUDA", "Triton"]},
    ),
    dict(
        company_name="Twilio", job_title="Developer Advocate",
        status=ApplicationStatus.WITHDRAWN,
        fit_score=0.62, fit_score_pct=62, fit_label="Good Fit",
        matched_skills=["Python", "REST APIs", "Node.js", "JavaScript"],
        missing_skills=["Technical Writing", "Public Speaking", "Ruby"],
        applied_date=_date(18), created_at=_dt(19),
        notes="Withdrew after accepting the Shopify offer.",
        job_description=(
            "Twilio is hiring a Developer Advocate to engage with our developer community. "
            "You'll create technical content, give talks, and build sample applications "
            "using Twilio APIs in Python, Ruby, and Node.js."
        ),
        jd_skills={"languages": ["Python", "Ruby", "JavaScript"], "frameworks": ["Node.js"], "tools": [], "concepts": ["REST APIs"], "other": ["Technical Writing", "Public Speaking"]},
    ),
    dict(
        company_name="Vercel", job_title="Full Stack Engineer",
        status=ApplicationStatus.APPLIED,
        fit_score=0.88, fit_score_pct=88, fit_label="Strong Fit",
        matched_skills=["React", "Next.js", "TypeScript", "Node.js", "PostgreSQL"],
        missing_skills=["Rust", "Edge Functions", "WebAssembly"],
        applied_date=_date(3), created_at=_dt(4),
        notes="Dream company for frontend infra. Resume tailored specifically for this role.",
        job_description=(
            "Vercel is looking for a Full Stack Engineer to build the future of web "
            "development tooling. You'll work with Next.js, TypeScript, and Rust to create "
            "Edge Functions and WebAssembly-based build tools."
        ),
        jd_skills={"languages": ["TypeScript", "Rust"], "frameworks": ["Next.js", "React", "Node.js"], "tools": ["PostgreSQL"], "concepts": ["REST APIs"], "other": ["Edge Functions", "WebAssembly"]},
    ),
]

# ─── Seed ─────────────────────────────────────────────────────────────────────

async def seed() -> None:
    async with AsyncSessionLocal() as session:

        # Step 1 — clean up existing demo user
        result = await session.execute(select(User).where(User.email == DEMO_EMAIL))
        existing = result.scalar_one_or_none()
        if existing:
            await session.delete(existing)
            await session.commit()
            print("Existing demo user removed.")

        # Create fresh user
        user = User(
            email=DEMO_EMAIL,
            full_name=DEMO_FULL_NAME,
            hashed_password=hash_password(DEMO_PASSWORD),
            is_active=True,
        )
        session.add(user)
        await session.flush()  # populate user.id before referencing it
        print(f"Created user: {DEMO_EMAIL}  (id={user.id})")

        # Step 2 — resume
        skill_count = sum(len(v) for v in PARSED_SKILLS.values())
        word_count = len(RESUME_TEXT.split())
        resume = Resume(
            user_id=user.id,
            raw_text=RESUME_TEXT,
            parsed_skills=PARSED_SKILLS,
            embedding_id=None,
            word_count=word_count,
        )
        session.add(resume)
        print(f"Created resume  ({skill_count} skills, {word_count} words)")

        # Step 3 — applications
        for data in APPS:
            app = JobApplication(
                user_id=user.id,
                company_name=data["company_name"],
                job_title=data["job_title"],
                job_description=data["job_description"],
                status=data["status"],
                fit_score=data["fit_score"],
                fit_score_pct=data["fit_score_pct"],
                fit_label=data["fit_label"],
                matched_skills=data["matched_skills"],
                missing_skills=data["missing_skills"],
                applied_date=data["applied_date"],
                jd_skills=data["jd_skills"],
                notes=data["notes"],
                created_at=data["created_at"],
            )
            session.add(app)

        await session.commit()

    # Step 4 — summary
    print()
    print("Demo data seeded successfully!")
    print(f"User: {DEMO_EMAIL} / {DEMO_PASSWORD}")
    print(f"Resume: created with {skill_count} skills")
    print("Applications: 12 created")
    print("Status breakdown:")
    print("  saved: 2, applied: 3, phone_screen: 1")
    print("  interview: 2, offer: 1, rejected: 2")
    print("  withdrawn: 1")


if __name__ == "__main__":
    asyncio.run(seed())
