# 📄 DocuMind

> **Ask questions about your documents. Get grounded answers.**

[![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-6.1-092E20?logo=django&logoColor=white)](https://www.djangoproject.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![pgvector](https://img.shields.io/badge/pgvector-Vector%20Search-336791)](https://github.com/pgvector/pgvector)
[![Celery](https://img.shields.io/badge/Celery-Background%20Jobs-37814A?logo=celery&logoColor=white)](https://docs.celeryq.dev/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![AWS](https://img.shields.io/badge/AWS-EC2-FF9900?logo=amazonaws&logoColor=white)](https://aws.amazon.com/ec2/)

**Live demo:** https://doccumind.duckdns.org/

DocuMind is a full-stack Django application for asking natural-language questions about uploaded **PDF and TXT documents**.

It uses **Retrieval-Augmented Generation (RAG)** to retrieve the most relevant parts of a document and provide only that context to Google's Gemini model before generating an answer.

```text
Upload document
      ↓
Extract text
      ↓
Split into overlapping chunks
      ↓
Generate embeddings
      ↓
Store in PostgreSQL + pgvector
      ↓
Embed user question
      ↓
Retrieve top-5 matching chunks
      ↓
Send context + question to Gemini
      ↓
Return grounded answer
```

---

## ✨ Why DocuMind?

A conventional LLM application might send an entire document to the model for every question.

DocuMind instead retrieves only the relevant information:

```text
Large document
      ↓
   Chunks
      ↓
Vector search
      ↓
Top 5 relevant chunks
      ↓
Gemini
      ↓
Grounded response
```

This keeps prompts focused, makes retrieval observable, and provides a practical foundation for scaling document-based Q&A.

---

## 🚀 Highlights

| Area | Implementation |
|---|---|
| **Web app** | Django 6.1 |
| **RAG** | Chunking → embeddings → pgvector retrieval → Gemini |
| **Embeddings** | `gemini-embedding-001`, 768 dimensions |
| **Answer generation** | `gemini-3.6-flash` |
| **Vector search** | PostgreSQL + `pgvector`, cosine distance |
| **Async processing** | Celery + Redis |
| **Authentication** | Django auth + email OTP |
| **Second factor** | Fresh email OTP on every login |
| **Frontend** | Django templates + HTMX |
| **API** | Django REST Framework + token authentication |
| **Containers** | Docker / Docker Compose |
| **Production** | Gunicorn + nginx + Let's Encrypt |
| **Hosting** | AWS EC2 |

---

# 📚 Table of Contents

- [Features](#-features)
- [Architecture](#-architecture)
- [How the RAG Pipeline Works](#-how-the-rag-pipeline-works)
- [Authentication and Security](#-authentication-and-security)
- [Data Model](#-data-model)
- [Project Structure](#-project-structure)
- [Tech Stack](#-tech-stack)
- [Run Locally](#-run-locally)
- [REST API](#-rest-api)
- [Testing](#-testing)
- [Docker](#-docker)
- [Production Deployment](#-production-deployment)
- [Configuration](#-configuration)
- [Troubleshooting](#-troubleshooting)
- [Current Limitations](#-current-limitations)
- [Roadmap](#-roadmap)
- [What This Project Demonstrates](#-what-this-project-demonstrates)
- [Author](#-author)

---

# ✨ Features

### 📄 Document Q&A
Upload a PDF or TXT document and ask questions about its contents.

### 🔍 Retrieval-Augmented Generation
Only the most relevant document chunks are passed to Gemini for answer generation.

### ⚙️ Background ingestion
Document extraction, chunking, and embedding happen asynchronously through Celery.

### ⚡ Live processing status
HTMX polling updates the document state without a full page refresh.

### 🤖 Grounded Gemini responses
The answer prompt instructs Gemini to use only the retrieved document context and acknowledge when the answer is not present.

### 🔐 Authentication + OTP
Signup requires email verification, and every login requires a fresh email OTP.

### 👤 Multi-user isolation
Documents are owned by users and are filtered by the authenticated user in both the web layer and API.

### 🔌 REST API
The same document and Q&A workflow can be accessed programmatically through a token-authenticated JSON API.

### 🌙 Dark mode
The UI supports a persisted light/dark theme preference.

### 🧪 Automated tests
The project includes tests for models, forms, chunking, authentication, document ownership, Celery dispatch, and Q&A behavior.

### 🐳 Production-ready container setup
The application is containerized and deployed with Gunicorn, nginx, HTTPS, PostgreSQL/pgvector, Redis, and Celery.

---

# 🏗️ Architecture

## High-level architecture

```text
                                      ┌────────────────────┐
                                      │      Browser       │
                                      └─────────┬──────────┘
                                                │ HTTPS
                                                ▼
                                      ┌────────────────────┐
                                      │   nginx container  │
                                      │ HTTP → HTTPS / TLS │
                                      └─────────┬──────────┘
                                                │
                                                ▼
                                      ┌────────────────────┐
                                      │ Django + Gunicorn  │
                                      │       web          │
                                      └───────┬────┬────────┘
                                              │    │
                               ┌──────────────┘    └──────────────┐
                               ▼                                  ▼
                     ┌──────────────────┐              ┌──────────────────┐
                     │ PostgreSQL       │              │      Redis       │
                     │ + pgvector       │              │  Celery broker   │
                     └────────┬─────────┘              └────────┬─────────┘
                              │                                   │
                              │                                   ▼
                              │                         ┌──────────────────┐
                              │                         │ Celery worker    │
                              │                         │ document ingest  │
                              │                         └────────┬─────────┘
                              │                                  │
                              └────────────────┬─────────────────┘
                                               │
                                               ▼
                                    ┌────────────────────┐
                                    │    Google Gemini   │
                                    │ embeddings + LLM   │
                                    └────────────────────┘
```

## Service responsibilities

| Service | Responsibility |
|---|---|
| **Django / Gunicorn** | Web requests, authentication, templates, document access, Q&A, REST API |
| **Celery worker** | Background document ingestion and embedding generation |
| **PostgreSQL + pgvector** | Users, documents, chunks, embeddings |
| **Redis** | Celery message broker |
| **nginx** | Reverse proxy, HTTP→HTTPS redirect, TLS termination |
| **Gemini API** | Embeddings and answer generation |

---

# 🧠 How the RAG Pipeline Works

## 1. Document upload

```text
User uploads PDF/TXT
        ↓
Django creates Document(status="processing")
        ↓
Celery task queued through Redis
        ↓
HTTP request returns
```

The user does not have to wait for the complete embedding process inside the upload request.

---

## 2. Text extraction

Supported formats:

```text
.pdf
.txt
```

The extraction layer converts both formats into plain text.

- TXT files are decoded as UTF-8.
- PDF text is extracted with `pypdf`.
- Unsupported extensions are rejected.

Implementation:

```text
qa/extraction.py
```

---

## 3. Chunking

The current chunking configuration is:

```text
Chunk size:  800 words
Overlap:     100 words
```

Example:

```text
Chunk 1
[1 ................................ 800]

Chunk 2
          [701 ......................... 1500]

Chunk 3
                    [1401 ...................... 2200]
```

The overlap helps preserve context across chunk boundaries.

Implementation:

```text
qa/chunking.py
```

---

## 4. Embeddings

Every chunk is converted into a vector using:

```text
gemini-embedding-001
```

The application uses:

```text
Dimensions: 768
```

Vectors are stored directly in PostgreSQL through `pgvector`.

Implementation:

```text
qa/embeddings.py
```

---

## 5. Retrieval

When a user asks a question:

```text
Question
   ↓
Question embedding
   ↓
768-dimensional vector
   ↓
pgvector cosine-distance search
   ↓
Top 5 chunks
```

Retrieval is performed against the selected document.

Implementation:

```text
qa/retrieval.py
```

---

## 6. Answer generation

The retrieved chunks and user's question are sent to:

```text
gemini-3.6-flash
```

The prompt explicitly instructs the model to use only the supplied document text.

Conceptually:

```text
Retrieved context
      +
User question
      ↓
Gemini
      ↓
Grounded answer
```

Implementation:

```text
qa/llm.py
```

---

## 7. Full ingestion flow

```text
                 ┌──────────────┐
                 │ PDF / TXT    │
                 └──────┬───────┘
                        ▼
                 ┌──────────────┐
                 │ Text extract │
                 └──────┬───────┘
                        ▼
                 ┌──────────────┐
                 │   Chunking   │
                 │ 800 / 100    │
                 └──────┬───────┘
                        ▼
                 ┌──────────────┐
                 │   Gemini     │
                 │  embeddings  │
                 └──────┬───────┘
                        ▼
                 ┌──────────────┐
                 │  PostgreSQL  │
                 │  + pgvector  │
                 └──────────────┘
```

---

# 🔐 Authentication and Security

## Signup

```text
Username + email + password
          ↓
User created as inactive
          ↓
6-digit signup OTP sent by email
          ↓
OTP verification
          ↓
Account activated
```

## Login

```text
Username + password
          ↓
Django authentication
          ↓
Fresh 6-digit OTP
          ↓
Email
          ↓
OTP verification
          ↓
Authenticated session
```

OTP codes expire after **10 minutes** and cannot be reused after successful verification.

---

## Document ownership

Every document belongs to a user:

```text
User
 └── Document
      └── Chunk
```

The application enforces ownership when retrieving documents.

A simplified access pattern is:

```python
Document.objects.filter(
    id=document_id,
    owner=request.user,
)
```

This is enforced in both the web views and API.

A user attempting to access another user's document receives a `404`, making that document effectively invisible from their account.

---

## Production security

When running with `DEBUG=False`, the application enables security-related Django settings including:

- Secure session cookies
- Secure CSRF cookies
- HTTPS redirects
- HSTS
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- Forwarded HTTPS handling through nginx

---

# 🗃️ Data Model

## Document

Represents an uploaded document.

| Field | Purpose |
|---|---|
| `owner` | User who owns the document |
| `file` | Uploaded PDF/TXT |
| `uploaded_at` | Upload timestamp |
| `status` | `processing`, `ready`, or `failed` |

## Chunk

Represents one searchable piece of a document.

| Field | Purpose |
|---|---|
| `document` | Parent document |
| `text` | Chunk content |
| `embedding` | 768-dimensional vector |
| `order` | Original chunk sequence |

## OTPCode

Represents a signup/login verification code.

| Field | Purpose |
|---|---|
| `user` | Associated user |
| `code` | Six-digit OTP |
| `purpose` | Signup or login |
| `channel` | Email |
| `created_at` | Creation time |
| `expires_at` | Expiration time |
| `is_used` | Prevents reuse |

---

# 📁 Project Structure

```text
Knowly/
├── manage.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
│
├── Knowly/
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   ├── asgi.py
│   └── celery.py
│
└── qa/
    ├── models.py
    ├── views.py
    ├── api_views.py
    ├── serializers.py
    ├── forms.py
    ├── urls.py
    │
    ├── extraction.py
    ├── chunking.py
    ├── embeddings.py
    ├── retrieval.py
    ├── llm.py
    ├── ingestion.py
    ├── tasks.py
    └── otp.py
    │
    ├── migrations/
    ├── templates/
    │   └── qa/
    ├── static/
    │   └── qa/
    └── tests/
        ├── test_chunking.py
        ├── test_forms.py
        ├── test_models.py
        └── test_views.py
```

## Core modules

| File | Responsibility |
|---|---|
| `extraction.py` | PDF/TXT → text |
| `chunking.py` | Text → overlapping chunks |
| `embeddings.py` | Text → Gemini vector |
| `retrieval.py` | pgvector similarity search |
| `llm.py` | Gemini prompt + answer |
| `ingestion.py` | Coordinates the ingestion pipeline |
| `tasks.py` | Celery task definitions |
| `otp.py` | OTP generation + email delivery |
| `views.py` | Web UI and authentication flows |
| `api_views.py` | REST API |
| `models.py` | Core database models |

---

# 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12+ |
| Framework | Django 6.1 |
| Database | PostgreSQL 16 |
| Vector extension | `pgvector` |
| Vector similarity | Cosine distance |
| Async jobs | Celery |
| Broker | Redis |
| Embeddings | `gemini-embedding-001` |
| LLM | `gemini-3.6-flash` |
| REST API | Django REST Framework |
| API auth | DRF TokenAuthentication |
| Frontend | Django Templates + HTMX |
| CSS | Custom CSS |
| PDF parsing | `pypdf` |
| Application server | Gunicorn |
| Reverse proxy | nginx |
| Containers | Docker / Docker Compose |
| TLS | Let's Encrypt / Certbot |
| Hosting | AWS EC2 |
| DNS | DuckDNS |

---

# 🚀 Run Locally

## Prerequisites

Install:

- Python **3.12+**
- Git
- Docker + Docker Compose
- Google Gemini API key
- SMTP credentials for email OTP delivery

---

## 1. Clone

```bash
git clone <your-repository-url>
cd Knowly
```

---

## 2. Create a virtual environment

### Linux / macOS

```bash
python3 -m venv venv
source venv/bin/activate
```

### Windows

```powershell
python -m venv venv
venv\Scripts\activate
```

---

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Start PostgreSQL + pgvector and Redis

```bash
docker compose up -d
```

Check:

```bash
docker compose ps
```

The development Compose setup provides PostgreSQL/pgvector and Redis.

---

## 5. Configure application settings

The application expects configuration for:

```text
DJANGO_SECRET_KEY
DJANGO_DEBUG
DJANGO_ALLOWED_HOSTS

GEMINI_API_KEY

POSTGRES_DB
POSTGRES_USER
POSTGRES_PASSWORD
POSTGRES_HOST
POSTGRES_PORT

CELERY_BROKER_URL

EMAIL_HOST_USER
EMAIL_HOST_PASSWORD
```

For the provided development database configuration, the defaults are:

```text
Database: documind
User:     documind
Password: documind
Host:     localhost
Port:     5432
```

The default Celery broker is:

```text
redis://localhost:6379/0
```

### Gmail OTP

DocuMind currently uses Gmail SMTP for OTP emails.

For Gmail accounts protected by 2-Step Verification, use a Google App Password rather than the normal account password.

---

## 6. Run migrations

```bash
python manage.py migrate
```

This initializes the Django database and pgvector extension used by the project.

---

## 7. Optional: create an admin user

```bash
python manage.py createsuperuser
```

Then:

```text
http://127.0.0.1:8000/admin/
```

---

## 8. Start Django

Terminal 1:

```bash
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/
```

---

## 9. Start Celery

Terminal 2:

```bash
celery -A Knowly worker --loglevel=info
```

### Windows

```bash
celery -A Knowly worker --loglevel=info --pool=solo
```

Keep the worker running while uploading documents.

---

# 🧪 First-Time Walkthrough

After starting Django and Celery:

```text
1. Open the application
2. Create an account
3. Verify the signup OTP
4. Log in
5. Verify the login OTP
6. Upload a PDF or TXT
7. Wait for Processing → Ready
8. Open the document
9. Ask a question
10. Review the grounded answer
```

---

# 🔌 REST API

The API uses Django REST Framework token authentication.

Every protected request requires:

```http
Authorization: Token <your_token>
```

## Get a token

```http
POST /api/token/
```

Example:

```bash
curl -X POST http://127.0.0.1:8000/api/token/ \
  -d "username=YOUR_USERNAME&password=YOUR_PASSWORD"
```

---

## List documents

```http
GET /api/documents/
```

```bash
curl http://127.0.0.1:8000/api/documents/ \
  -H "Authorization: Token YOUR_TOKEN"
```

Only documents owned by the authenticated user are returned.

---

## Upload a document

```http
POST /api/documents/
```

```bash
curl -X POST http://127.0.0.1:8000/api/documents/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -F "file=@example.pdf"
```

The document is created and processing is queued asynchronously.

---

## Get one document

```http
GET /api/documents/<id>/
```

```bash
curl http://127.0.0.1:8000/api/documents/5/ \
  -H "Authorization: Token YOUR_TOKEN"
```

---

## Ask a question

```http
POST /api/documents/<id>/ask/
```

```bash
curl -X POST http://127.0.0.1:8000/api/documents/5/ask/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question":"What is this document about?"}'
```

Example response:

```json
{
  "question": "What is this document about?",
  "answer": "..."
}
```

If the document is still being processed:

```http
409 Conflict
```

```json
{
  "error": "Document is not ready yet"
}
```

---

# 🧪 Testing

Run the full test suite with:

```bash
python manage.py test
```

The current suite contains **15 tests** covering:

- Model behavior
- Default document status
- Chunk ordering
- Chunk splitting and overlap
- Form validation
- Authentication enforcement
- Document ownership
- Cross-user isolation
- Celery task dispatch
- Question answering
- HTMX-aware responses

External Gemini and Celery operations are mocked where appropriate, so the suite does not depend on real AI API calls.

---

# 🐳 Docker

The project includes a Dockerfile for the application image.

The image:

1. Uses `python:3.12-slim`
2. Installs required system packages
3. Installs Python dependencies
4. Copies the project
5. Collects static files
6. Runs Gunicorn on port `8000`

The production web service runs:

```bash
gunicorn Knowly.wsgi:application --bind 0.0.0.0:8000 --workers 3
```

---

# 🌐 Production Deployment

DocuMind is deployed on **AWS EC2** using Docker Compose.

The production stack contains:

```text
nginx
web
worker
db
redis
```

Persistent volumes are used for:

```text
pgdata
media
certbot_www
certbot_certs
```

## Production architecture

```text
                         Internet
                            │
                         :80/:443
                            ▼
                  ┌────────────────────┐
                  │   nginx container  │
                  │  HTTP → HTTPS/TLS  │
                  └─────────┬──────────┘
                            │
                            ▼
                  ┌────────────────────┐
                  │     web container  │
                  │ Django + Gunicorn  │
                  │       :8000        │
                  └──────┬─────┬───────┘
                         │     │
               ┌─────────┘     └─────────┐
               ▼                         ▼
      ┌──────────────────┐      ┌──────────────────┐
      │ PostgreSQL       │      │ Redis            │
      │ + pgvector       │      │ Celery broker    │
      └────────┬─────────┘      └────────┬─────────┘
               ▲                         │
               │                         ▼
               │                ┌──────────────────┐
               └────────────────│ Celery worker    │
                                └────────┬─────────┘
                                         │
                                         ▼
                                ┌──────────────────┐
                                │   Gemini API     │
                                └──────────────────┘
```

---

## Production Compose services

### `db`

```text
pgvector/pgvector:pg16
```

Stores users, documents, chunks, and vector embeddings.

### `redis`

```text
redis:7-alpine
```

Celery message broker.

### `web`

Built from the project Dockerfile and served with Gunicorn.

### `worker`

Uses the same application image and runs:

```bash
celery -A Knowly worker --loglevel=info
```

### `nginx`

```text
nginx:alpine
```

Exposes:

```text
80
443
```

and proxies traffic to:

```text
web:8000
```

---

# 🔒 HTTPS / nginx

The production nginx configuration:

- Listens on port `80`
- Serves the Let's Encrypt ACME challenge
- Redirects normal HTTP traffic to HTTPS
- Listens on port `443`
- Loads the Let's Encrypt certificate
- Proxies requests to `web:8000`

Certificates are persisted through Docker volumes.

The production domain is:

```text
doccumind.duckdns.org
```

---

# ⚙️ Production Deployment Flow

A typical deployment flow is:

```text
Clone repository
      ↓
Configure production settings
      ↓
Build application image
      ↓
Start Docker Compose production stack
      ↓
Run Django migrations
      ↓
Verify nginx + HTTPS
      ↓
Verify Celery worker
      ↓
Upload test document
      ↓
Run end-to-end RAG test
```

The production Compose file used on the EC2 server is:

```text
docker-compose.prod.yml
```

and the nginx configuration is:

```text
nginx.conf
```

---

# 📌 Useful Commands

### Start local infrastructure

```bash
docker compose up -d
```

### Stop local infrastructure

```bash
docker compose down
```

### Run migrations

```bash
python manage.py migrate
```

### Run tests

```bash
python manage.py test
```

### Run Django

```bash
python manage.py runserver
```

### Run Celery

```bash
celery -A Knowly worker --loglevel=info
```

### Create admin user

```bash
python manage.py createsuperuser
```

### Collect static files

```bash
python manage.py collectstatic
```

---

# 🧪 Recommended RAG Evaluation

A useful test document should contain predictable information such as:

- Company details
- Dates
- Pricing
- Policies
- Limits
- Support SLAs
- Security rules

Then test several question types.

### Direct retrieval

```text
What is the company called?
```

### Numerical retrieval

```text
What is the API request limit?
```

### Conditional retrieval

```text
What happens after five failed login attempts?
```

### Multi-part retrieval

```text
What are the plan price, API limit, and support SLA?
```

### Negative / hallucination test

```text
Who is the CEO?
```

For information that is genuinely absent from the document, the desired behavior is an explicit acknowledgement that it is not available rather than an invented answer.

---

# ⚠️ Troubleshooting

## Documents remain in `processing`

Check that:

```text
Redis is running
Celery worker is running
Gemini API access is working
PostgreSQL is reachable
```

For Docker:

```bash
docker compose ps
```

---

## Gemini requests fail

Check the configured:

```text
GEMINI_API_KEY
```

and verify access to the models used by the project.

---

## PostgreSQL connection fails

Check the database container:

```bash
docker compose ps
```

and verify:

```text
POSTGRES_HOST
POSTGRES_PORT
POSTGRES_DB
POSTGRES_USER
POSTGRES_PASSWORD
```

---

## Redis connection fails

Verify Redis is running and that the Celery broker URL points to:

```text
redis://localhost:6379/0
```

for local host-based execution.

---

## OTP email does not arrive

Check:

- SMTP credentials
- Gmail App Password
- Spam/junk folder
- `EMAIL_HOST_USER`
- `EMAIL_HOST_PASSWORD`

OTP codes expire after **10 minutes**.

---

## API returns `409 Conflict`

For:

```http
POST /api/documents/<id>/ask/
```

a `409` response means the document has not reached:

```text
status = "ready"
```

Wait for background processing to finish and retry.

---

# 📏 RAG Configuration

The current implementation uses:

| Parameter | Value |
|---|---:|
| Chunk size | 800 words |
| Chunk overlap | 100 words |
| Embedding model | `gemini-embedding-001` |
| Embedding dimensions | 768 |
| Retrieval Top-K | 5 |
| Answer model | `gemini-3.6-flash` |
| OTP lifetime | 10 minutes |

These values are implementation defaults and can be tuned as retrieval evaluation improves.

---

# 🧭 Current Limitations

The current project intentionally keeps the RAG pipeline straightforward.

Potential future improvements include:

- More document formats
- Better handling of PDF tables/layouts
- Hybrid keyword + vector retrieval
- Reranking
- Query rewriting
- Streaming responses
- Conversation history
- Source/page citations
- S3-backed file storage
- Usage tiers / billing
- SMS OTP
- Structured logging
- Monitoring and metrics
- Larger automated RAG evaluation datasets

---

# 🗺️ Roadmap

```text
[x] PDF/TXT ingestion
[x] Text chunking
[x] Gemini embeddings
[x] pgvector retrieval
[x] Gemini grounded answers
[x] Background document processing
[x] Email OTP authentication
[x] REST API
[x] User/document isolation
[x] Docker deployment
[x] HTTPS
[x] AWS EC2 deployment

[ ] SMS OTP
[ ] Billing / usage tiers
[ ] S3-backed storage
[ ] Advanced retrieval / reranking
[ ] Source citations
[ ] Structured logging & monitoring
[ ] Expanded RAG evaluation
```

---

# 🎯 What This Project Demonstrates

DocuMind combines several areas into one end-to-end application.

### Backend engineering

- Django
- ORM
- Authentication
- File uploads
- Forms
- REST APIs
- Authorization
- Security

### Generative AI

- Embeddings
- LLM integration
- Prompt design
- Retrieval-Augmented Generation
- Context construction
- Hallucination mitigation

### Data / search

- PDF text extraction
- Chunking
- Vector storage
- Similarity search

### Asynchronous systems

- Celery
- Redis
- Background jobs

### DevOps

- Docker
- Docker Compose
- Gunicorn
- nginx
- Let's Encrypt
- AWS EC2

---

# 👨‍💻 Author

**Rahul Rathod**

Python Developer · Django · RAG · Generative AI · AWS

**Live application:** https://doccumind.duckdns.org/

---

## 📜 License

Add the repository license here when one is selected, for example:

```text
MIT License
```
