"""Shared builders for the Situation Room tests."""
from app.services import events as svc


def article(title, description="", *, n=None, published="2026-11-08T12:00:00Z", source="UN News", source_country=None):
    n = n if n is not None else abs(hash(title)) % 10**8
    return {"title": title, "description": description, "url": f"https://example.com/{n}",
            "published": published, "source": source, "domain": "example.com",
            "source_country": source_country, "topics": []}


def event(title, description="", **kw):
    return svc.build_event(article(title, description, **kw))
