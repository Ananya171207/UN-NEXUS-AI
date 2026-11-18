"""Response schemas for the events endpoints.

Field names are camelCase to match the frontend contract exactly.
"""
from pydantic import BaseModel, Field


class ClassificationInfo(BaseModel):
    method: str = Field(description="How the labels were produced: 'rules' now; 'llm' in a later stage.")
    aiGenerated: bool = Field(description="True when an AI model produced category/severity.")
    signals: list[str] = Field(description="The words/rules that led to the labels (for transparency).")


class LocationEvidence(BaseModel):
    field: str = Field(description="'title' or 'description': where the country name was found.")
    match: str = Field(description="The name exactly as written in the article.")
    rule: str = Field(description="headline_prefix | place_word | single_mention | city_place_word | city_headline_prefix | city_mention | llm_quote | ambiguous_name")


class EventLocation(BaseModel):
    status: str = Field(description="'assigned' (countryId is set) or 'ambiguous' (several candidates; countryId stays null).")
    method: str = Field(description="'gazetteer-title', 'gazetteer-description' or 'llm-validated'.")
    confidence: str | None = Field(None, description="'high' | 'medium'. Null when ambiguous.")
    precision: str | None = Field(None, description="'city' (event has coordinates) or 'country' (country only). Null when ambiguous.")
    city: str | None = Field(None, description="The city the coordinates refer to, when precision is 'city'.")
    evidence: list[LocationEvidence] = Field(description="The wording that supports the decision.")
    candidates: list[str] = Field(description="ISO alpha-2 codes of every country the text named or could mean.")


class EventOut(BaseModel):
    id: str = Field(description="Stable id derived from the article URL. Safe as a React key.")
    title: str
    summary: str | None = Field(None, description="Article description from the source; null if the source gives none.")
    url: str | None = Field(None, description="Original article URL.")
    occurredAt: str = Field(description="ISO-8601 UTC time the article was published (not necessarily when the event happened).")
    source: str = Field(description="'UN News' or 'GDELT'.")
    sourceDomain: str | None = None
    sourceCountry: str | None = Field(None, description="Country of the PUBLISHER. Not the event location.")
    category: str
    severity: str = Field(description="low | moderate | high | critical")
    topics: list[str] = []
    classification: ClassificationInfo
    countryId: str | None = Field(None, description="ISO alpha-2 id matching /api/countries. Null = global/unknown.")
    countryCode3: str | None = None
    countryName: str | None = None
    region: str | None = Field(None, description="Continental region (6 regions; Middle East countries sit in Asia/Africa). Unchanged.")
    monitoringRegion: str | None = Field(None, description="Region used by the regional monitor (7 regions, including Middle East). Null when the country is unknown.")
    latitude: float | None = Field(None, description="Event-specific latitude. Null unless a verified city-level location exists.")
    longitude: float | None = None
    locationMethod: str | None = Field(None, description="How the location was determined; null when unknown.")
    location: EventLocation | None = Field(None, description="Evidence behind countryId. Null when the text names no country.")
    isSample: bool = False


class SourceStatus(BaseModel):
    source: str
    status: str = Field(description="never_fetched | ok | error | rate_limited")
    lastAttempt: str | None = None
    lastSuccess: str | None = None
    lastError: str | None = None
    articleCount: int = 0
    cooldownRemainingSeconds: int = Field(0, description="Seconds before this source will be contacted again.")


class CountryEventsOut(BaseModel):
    countryId: str = Field(description="ISO alpha-2 (the frontend id).")
    countryCode: str = Field(description="ISO alpha-3.")
    countryName: str
    total: int = Field(description="All events matching the filters, before limit/offset.")
    limit: int
    offset: int
    events: list[EventOut]
    note: str = Field(description="How events are linked to the country (and what is left out).")
