# 🧠 JobTracker AI

> AI-powered job application tracker with resume matching, skill gap analysis, and intelligent suggestions.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-15-000000?style=flat-square&logo=next.js&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1?style=flat-square&logo=mysql&logoColor=white)
![Gemini AI](https://img.shields.io/badge/Google_Gemini-AI-4285F4?style=flat-square&logo=google&logoColor=white)
![Pinecone](https://img.shields.io/badge/Pinecone-Vector_DB-00B388?style=flat-square)

---

## 🎥 Demo

**Try it with the demo account:**

```
Email:    demo@jobtracker.ai
Password: Demo1234!
```

---

## ✨ Features

**Resume analysis and skill extraction.** Upload a PDF resume or paste plain text and the system extracts every skill — languages, frameworks, tools, and concepts — using Google Gemini. Skills are stored against your profile and used as the baseline for every fit score calculation across your applications.

**AI-powered job fit scoring.** When you save a job description, the backend generates a semantic embedding via Gemini and queries Pinecone for similarity against your resume embedding. A separate skill-overlap ratio is computed by comparing the job's required skills against your extracted resume skills. The two signals are blended into a single 0–100 fit score (see [How the Fit Score Works](#-how-the-fit-score-works)).

**Application tracking with Kanban board.** Track every application through seven stages — Saved, Applied, Phone Screen, Interview, Offer, Rejected, and Withdrawn — either as a sortable table or a drag-and-drop Kanban board. Inline status updates sync immediately to the backend without a full page reload.

**Analytics dashboard with charts.** The dashboard surfaces a weekly applications timeline, a status breakdown donut chart, and a horizontal bar chart of your top skill gaps — skills that appear most frequently in job descriptions you have not yet acquired. KPI cards show total applications, average fit score, interview rate, and pending-analysis count at a glance.

**Resume improvement suggestions.** For each application, Gemini generates targeted bullet-point suggestions for how to reframe your resume against that specific job description, calling out skills to add, talking points to emphasise, and gaps to address before applying.

---

## 🏗️ Architecture

```
┌─────────────┐     ┌─────────────┐     ┌──────────────┐
│  Next.js 15 │────▶│   FastAPI   │────▶│    MySQL     │
│  Frontend   │     │   Backend   │     │   Database   │
└─────────────┘     └──────┬──────┘     └──────────────┘
                           │
                 ┌─────────┴──────────┐
                 │                    │
          ┌──────▼──────┐    ┌───────▼──────┐
          │ Gemini 2.0  │    │   Pinecone   │
          │  Flash AI   │    │Vector Search │
          └─────────────┘    └──────────────┘
```

The Next.js frontend talks exclusively to the FastAPI backend over a REST API. The backend owns all business logic, persists relational data in MySQL via SQLAlchemy async, offloads AI inference to Google Gemini, and stores/queries resume + job description embeddings in Pinecone.

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | Next.js 15, React 18, TypeScript 5 | App shell, routing, server components |
| **UI** | Tailwind CSS, shadcn/ui, Recharts | Styling, component library, charts |
| **Backend** | FastAPI 0.115, Python 3.11, Uvicorn | REST API, async request handling |
| **ORM / Migrations** | SQLAlchemy 2.0 (async), Alembic 1.14 | Database models and schema versioning |
| **Database** | MySQL 8.0 + aiomysql | Relational persistence |
| **Vector DB** | Pinecone | Semantic similarity search |
| **AI / ML** | Google Gemini 2.0 Flash, `google-generativeai` | Resume parsing, fit scoring, suggestions |
| **Auth** | JWT (python-jose), bcrypt | Stateless token authentication |
| **PDF Parsing** | pdfplumber | Extract text from uploaded resume PDFs |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- Node.js 20+
- MySQL 8.0+ (running locally on port 3306)
- [Gemini API key](https://ai.google.dev) — free tier is sufficient
- [Pinecone account](https://www.pinecone.io) — free tier is sufficient

### 1. Clone the repository

```bash
git clone https://github.com/OmPatel1493/job-tracker.git
cd job-tracker
```

### 2. Backend setup

```bash
cd backend

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt
```

Create a `.env` file in the `backend/` directory:

```bash
cp .env.example .env
```

Fill in the values:

```env
DATABASE_URL=mysql+aiomysql://root:yourpassword@localhost:3306/jobtracker
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
GEMINI_API_KEY=your-gemini-api-key
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_ENVIRONMENT=us-east-1
PINECONE_INDEX_NAME=jobtracker-resumes
```

Run database migrations and start the server:

```bash
# Create the MySQL database first
mysql -u root -p -e "CREATE DATABASE jobtracker CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# Run all migrations
alembic upgrade head

# Start the backend (runs on http://localhost:8000)
uvicorn app.main:app --reload
```

### 3. Frontend setup

Open a new terminal:

```bash
cd frontend
npm install
```

Create a `.env.local` file in the `frontend/` directory:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Start the development server:

```bash
# Runs on http://localhost:3000
npm run dev
```

### 4. Seed demo data

With the backend running, populate the database with 12 realistic sample applications and a demo user account:

```bash
cd backend
python seed.py
```

The demo account credentials are: `demo@jobtracker.ai` / `Demo1234!`

---

## 📡 API Endpoints

### Auth

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|:---:|
| `POST` | `/auth/register` | Register a new user | No |
| `POST` | `/auth/login` | Log in, receive JWT token | No |
| `GET` | `/auth/me` | Get current user profile | Yes |

### Resume

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|:---:|
| `POST` | `/resume/upload` | Upload PDF or paste text, trigger AI parsing | Yes |
| `GET` | `/resume` | Get parsed resume with extracted skills | Yes |
| `DELETE` | `/resume` | Delete current resume | Yes |

### Applications

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|:---:|
| `GET` | `/applications` | List all applications (filter, sort, paginate) | Yes |
| `POST` | `/applications` | Create a new application | Yes |
| `GET` | `/applications/{id}` | Get a single application with analysis | Yes |
| `PATCH` | `/applications/{id}` | Update status, notes, or fields | Yes |
| `DELETE` | `/applications/{id}` | Delete an application | Yes |

### AI Suggestions

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|:---:|
| `POST` | `/suggestions/{application_id}` | Generate AI improvement suggestions | Yes |
| `GET` | `/suggestions/{application_id}` | Retrieve stored suggestions | Yes |

### Analytics

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|:---:|
| `GET` | `/analytics/summary` | KPIs, status breakdown, skill gaps, weekly trend | Yes |

---

## 📁 Project Structure

```bash
job-tracker/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, router registration, CORS
│   │   ├── config.py            # Pydantic settings (reads .env)
│   │   ├── database.py          # Async SQLAlchemy engine + session factory
│   │   ├── dependencies.py      # get_current_user dependency
│   │   ├── models/              # SQLAlchemy ORM models (User, Application, Resume, …)
│   │   ├── routers/             # FastAPI routers (auth, applications, resume, …)
│   │   ├── schemas/             # Pydantic request/response schemas
│   │   ├── services/            # Business logic (AI scoring, skill extraction, …)
│   │   └── utils/               # PDF parsing, token helpers
│   ├── alembic/                 # Database migrations
│   │   └── versions/            # Migration scripts
│   ├── seed.py                  # Populate DB with demo data
│   ├── requirements.txt
│   └── .env.example
│
└── frontend/
    ├── app/
    │   ├── (auth)/              # Login + register pages (unauthenticated layout)
    │   └── (app)/               # Authenticated app shell
    │       ├── layout.tsx        # Sidebar + TopBar shell
    │       ├── dashboard/        # Overview KPIs and charts
    │       ├── applications/     # List, Kanban, and detail pages
    │       ├── resume/           # Resume upload and skill breakdown
    │       └── analytics/        # Full analytics page
    ├── components/
    │   ├── layout/               # Sidebar.tsx, TopBar.tsx
    │   ├── ui/                   # shadcn/ui primitives + LoadingSpinner
    │   ├── ApplicationCard.tsx
    │   ├── ApplicationForm.tsx
    │   ├── StatusKanban.tsx
    │   ├── FitScoreGauge.tsx
    │   └── ErrorBoundary.tsx
    ├── lib/
    │   ├── api.ts                # Axios client + all API call functions
    │   └── types.ts              # TypeScript interfaces matching backend schemas
    ├── contexts/
    │   └── AuthContext.tsx       # JWT token management, login/logout
    └── middleware.ts             # Redirect unauthenticated users to /login
```

---

## 🧮 How the Fit Score Works

Each application is scored on a 0–100 scale using two signals:

**Semantic similarity (60% weight).** When you save a job description, the backend generates an embedding using Gemini and queries your resume embedding stored in Pinecone. The cosine similarity score (0–1) represents how closely your overall experience matches the role, even when different words are used for the same concept.

**Skill overlap ratio (40% weight).** The job description is parsed to extract required skills, which are then compared against the skills extracted from your resume. The ratio of matched skills to total required skills gives a precise keyword-level score.

**Final formula:**

```
fit_score = (semantic_similarity × 0.6) + (skill_overlap_ratio × 0.4)
fit_score_pct = round(fit_score × 100)
```

**Score labels:**

| Score | Label |
|-------|-------|
| 0–20 | Poor |
| 21–40 | Moderate |
| 41–60 | Good |
| 61–80 | Strong |
| 81–100 | Excellent |

---

## 👨‍💻 Author

Built by Om Patel as a portfolio project.

---

## 📄 License

MIT
