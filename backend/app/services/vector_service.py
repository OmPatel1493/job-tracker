"""
Pinecone vector service — stores and queries resume embeddings.

WHY vector embeddings:
  Raw text cannot be compared by similarity directly. Embeddings convert text
  into a fixed-length list of floats (a vector) where similar meanings sit
  close together in vector space. Pinecone stores these vectors and can find
  the closest match to any query vector in milliseconds.

WHY Gemini for embeddings (not OpenAI):
  Google's text-embedding-004 model is available on the free API tier.
  It produces 768-dimensional vectors with strong semantic accuracy.
  Same GEMINI_API_KEY used by the skill extractor — no extra credentials.

WHY task_type matters for Gemini embeddings:
  Gemini optimises embeddings differently depending on use case.
  "retrieval_document" is used when storing a document (resume) in the index.
  "retrieval_query" is used when querying (job description lookup).
  Using the correct task_type improves match quality significantly.

IMPORTANT — Pinecone index setup (one-time manual step):
  Before using this service, create a Pinecone index with these settings:
    name      : value of PINECONE_INDEX_NAME in your .env
    dimension : 768   ← Gemini text-embedding-004 output size (NOT 1536)
    metric    : cosine
  Create it at https://app.pinecone.io or via the Pinecone console.
  If you use dimension=1536 (OpenAI default) the upsert will fail silently.
"""

import google.generativeai as genai
from pinecone import Pinecone

from app.config import settings

# ---------------------------------------------------------------------------
# Client initialisation
# ---------------------------------------------------------------------------

# Both clients are module-level singletons — created once when the module is
# first imported. Lazy checks inside each function guard against missing keys.

_pinecone_client: Pinecone | None = None
_pinecone_index = None


def _get_index():
    """
    Return the Pinecone index, initialising the client on first call.

    WHY lazy init: the module is imported at startup before the user has
    necessarily set PINECONE_API_KEY. Lazy init defers the error to the
    first actual call, keeping startup clean.
    """
    global _pinecone_client, _pinecone_index
    if _pinecone_index is None:
        if not settings.PINECONE_API_KEY:
            raise RuntimeError(
                "PINECONE_API_KEY is not set. Add it to your .env file."
            )
        if not settings.PINECONE_INDEX_NAME:
            raise RuntimeError(
                "PINECONE_INDEX_NAME is not set. Add it to your .env file."
            )
        _pinecone_client = Pinecone(api_key=settings.PINECONE_API_KEY)
        _pinecone_index = _pinecone_client.Index(settings.PINECONE_INDEX_NAME)
    return _pinecone_index


# ---------------------------------------------------------------------------
# Embedding
# ---------------------------------------------------------------------------

def generate_embedding(text: str, task_type: str = "retrieval_document") -> list[float]:
    """
    Generate a 768-dimensional embedding vector for the given text using
    Google's text-embedding-004 model.

    Args:
        text:      The text to embed. Truncated to 8000 characters if longer.
        task_type: "retrieval_document" for storage, "retrieval_query" for search.

    Returns:
        A list of 768 floats representing the text in vector space.

    Raises:
        RuntimeError: if GEMINI_API_KEY is missing or the API call fails.

    WHY 8000 char truncation:
        text-embedding-004 has a 2048 token limit (roughly 8000 chars).
        Truncating avoids an API error for very long resumes while keeping
        the most content-rich section (the top of a resume).
    """
    if not settings.GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Add it to your .env file."
        )

    genai.configure(api_key=settings.GEMINI_API_KEY)

    truncated = text[:8000] if len(text) > 8000 else text

    try:
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=truncated,
            task_type=task_type,
        )
        return result["embedding"]
    except Exception as exc:
        raise RuntimeError(f"Gemini embedding API call failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Pinecone operations
# ---------------------------------------------------------------------------

def upsert_resume_embedding(user_id: str, resume_id: str, text: str) -> str:
    """
    Embed a resume and store (or overwrite) the vector in Pinecone.

    Args:
        user_id:   The authenticated user's ID (used as a filter key).
        resume_id: A unique identifier for this resume version.
        text:      The plain text of the resume (from pdf_service).

    Returns:
        The vector_id that was upserted (use this to delete later).

    WHY composite vector_id:
        Pinecone requires globally unique IDs. Prefixing with "resume_"
        and including user_id prevents collisions between users.
    """
    vector_id = f"resume_{user_id}_{resume_id}"
    embedding = generate_embedding(text, task_type="retrieval_document")

    try:
        index = _get_index()
        index.upsert(vectors=[{
            "id": vector_id,
            "values": embedding,
            "metadata": {
                "type": "resume",
                "user_id": user_id,
                "resume_id": resume_id,
            },
        }])
        return vector_id
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"Pinecone upsert failed: {exc}") from exc


def query_similar_to_jd(jd_text: str, user_id: str, top_k: int = 1) -> float:
    """
    Find how well the user's stored resume matches a job description.

    Embeds the job description text and queries Pinecone for the closest
    resume vector belonging to this user.

    Args:
        jd_text: The plain text of the job description.
        user_id: Filter queries to this user's resumes only.
        top_k:   Number of results to retrieve (default 1 — best match).

    Returns:
        Cosine similarity score (0.0 to 1.0) of the top match.
        Returns 0.0 if no resume has been stored for this user yet.

    WHY filter by user_id:
        All users share one Pinecone index. Without a filter, a query could
        return another user's resume as the top match. Metadata filters
        ensure each user only sees their own vectors.
    """
    embedding = generate_embedding(jd_text, task_type="retrieval_query")

    try:
        index = _get_index()
        results = index.query(
            vector=embedding,
            top_k=top_k,
            filter={"user_id": user_id, "type": "resume"},
            include_metadata=True,
        )
        matches = results.get("matches", [])
        if not matches:
            return 0.0
        return float(matches[0].get("score", 0.0))
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"Pinecone query failed: {exc}") from exc


def delete_resume_embedding(vector_id: str) -> bool:
    """
    Remove a resume vector from Pinecone by its vector_id.

    Args:
        vector_id: The ID returned by upsert_resume_embedding.

    Returns:
        True if the delete succeeded, False if it failed for any reason.

    WHY return bool (not raise):
        Deletion failures are non-critical — the worst outcome is a stale
        vector in Pinecone. Returning False lets callers log the failure
        without crashing the request that triggered it.
    """
    try:
        index = _get_index()
        index.delete(ids=[vector_id])
        return True
    except Exception:
        return False


def check_pinecone_connection() -> bool:
    """
    Verify that the Pinecone index is reachable and responding.

    Returns:
        True if describe_index_stats() succeeds, False on any error.

    WHY this function:
        Used by health check or admin endpoints to confirm the vector DB
        is up before attempting upserts or queries.
    """
    try:
        index = _get_index()
        index.describe_index_stats()
        return True
    except Exception:
        return False
