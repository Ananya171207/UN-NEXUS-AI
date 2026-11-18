"""Central configuration.

Every value can be overridden with an environment variable (or a `.env` file
in the backend folder). Nothing secret lives in this file.
"""
import logging
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning("Ignoring invalid integer for %s: %r", name, raw)
        return default


def _get_list(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    raw = os.getenv(name)
    if not raw:
        return default
    return tuple(part.strip() for part in raw.split(",") if part.strip())


@dataclass(frozen=True)
class Settings:
    # Frontend dev server (Vite). Add your deployed frontend URL in production.
    cors_origins: tuple[str, ...]
    user_agent: str

    # How long a successful fetch is reused before asking the source again.
    un_news_cache_seconds: int
    gdelt_cache_seconds: int
    events_cache_seconds: int

    # Circuit breaker: after a failure the source is left alone for this long.
    gdelt_cooldown_seconds: int  # used when GDELT answers 429 without Retry-After
    source_error_cooldown_seconds: int  # used for timeouts / 5xx / bad payloads

    un_news_fetch_limit: int
    gdelt_fetch_limit: int
    un_news_timeout: int
    gdelt_timeout: int
    # How long a request waits for each source before answering without it. The slow
    # source keeps loading in the background and is used by the next request.
    un_news_wait_seconds: float
    gdelt_wait_seconds: float

    # World Bank + country metadata
    worldbank_timeout: int
    worldbank_retries: int  # extra attempts after a timeout / connection error / 5xx
    worldbank_cache_seconds: int
    worldbank_profile_deadline: float  # max seconds a profile request waits; slower indicators become "pending"
    countries_cache_seconds: int
    countries_retry_seconds: int  # wait before retrying REST Countries after a failure
    countries_timeout: int
    countries_snapshot_path: str

    # SDG signals
    sdg_outdated_years: int  # a value older than this many years is flagged `outdated`

    # AI layer (all optional: with no key the API works with rule-based fallbacks)
    llm_provider: str  # "none" | "gemini" | "openai"
    llm_model: str
    llm_api_key: str  # read from the environment only; never logged or returned
    groq_api_key: str
    groq_model: str
    llm_timeout: int
    llm_cooldown_seconds: int  # after a failed call the LLM is left alone for this long
    llm_max_calls_per_hour: int  # hard cap on spend
    ai_batch_size: int  # events per LLM call
    ai_cache_path: str
    admin_token: str  # if set, POST /api/events/enrich needs the header X-Admin-Token

    log_level: str
    rest_countries_api_key: str = ""


def load_settings() -> Settings:
    return Settings(
        cors_origins=_get_list(
            "CORS_ORIGINS", ("http://localhost:5173", "http://127.0.0.1:5173")
        ),
        user_agent=os.getenv("USER_AGENT", "UN-NEXUS-AI/1.0"),
        un_news_cache_seconds=_get_int("UN_NEWS_CACHE_SECONDS", 300),
        gdelt_cache_seconds=_get_int("GDELT_CACHE_SECONDS", 900),
        events_cache_seconds=_get_int("EVENTS_CACHE_SECONDS", 120),
        gdelt_cooldown_seconds=_get_int("GDELT_COOLDOWN_SECONDS", 900),
        source_error_cooldown_seconds=_get_int("SOURCE_ERROR_COOLDOWN_SECONDS", 120),
        un_news_fetch_limit=_get_int("UN_NEWS_FETCH_LIMIT", 50),
        gdelt_fetch_limit=_get_int("GDELT_FETCH_LIMIT", 75),
        un_news_timeout=_get_int("UN_NEWS_TIMEOUT", 15),
        gdelt_timeout=_get_int("GDELT_TIMEOUT", 15),
        un_news_wait_seconds=float(_get_int("UN_NEWS_WAIT_SECONDS", 12)),
        gdelt_wait_seconds=float(_get_int("GDELT_WAIT_SECONDS", 4)),
        worldbank_timeout=_get_int("WORLDBANK_TIMEOUT", 5),
        worldbank_retries=_get_int("WORLDBANK_RETRIES", 2),
        worldbank_cache_seconds=_get_int("WORLDBANK_CACHE_SECONDS", 86400),
        worldbank_profile_deadline=float(_get_int("WORLDBANK_PROFILE_DEADLINE", 12)),
        countries_cache_seconds=_get_int("COUNTRIES_CACHE_SECONDS", 604800),
        countries_retry_seconds=_get_int("COUNTRIES_RETRY_SECONDS", 300),
        countries_timeout=_get_int("COUNTRIES_TIMEOUT", 15),
        rest_countries_api_key=os.getenv("REST_COUNTRIES_API_KEY", "").strip(),
        countries_snapshot_path=os.getenv(
            "COUNTRIES_SNAPSHOT_PATH",
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "countries_snapshot.json"),
        ),
        sdg_outdated_years=_get_int("SDG_OUTDATED_YEARS", 5),
        llm_provider=os.getenv("LLM_PROVIDER", "none").strip().lower() or "none",
        llm_model=os.getenv("LLM_MODEL", "").strip(),
        llm_api_key=os.getenv("LLM_API_KEY", "").strip(),
        groq_api_key=os.getenv("GROQ_API_KEY", "").strip(),
        groq_model=os.getenv(
            "GROQ_MODEL", "openai/gpt-oss-20b"
        ).strip(),
        llm_timeout=_get_int("LLM_TIMEOUT", 20),
        llm_cooldown_seconds=_get_int("LLM_COOLDOWN_SECONDS", 120),
        llm_max_calls_per_hour=_get_int("LLM_MAX_CALLS_PER_HOUR", 60),
        ai_batch_size=_get_int("AI_BATCH_SIZE", 8),
        ai_cache_path=os.getenv(
            "AI_CACHE_PATH",
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "ai_cache.sqlite3"),
        ),
        admin_token=os.getenv("ADMIN_TOKEN", "").strip(),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),

    )


settings = load_settings()


def configure_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )
