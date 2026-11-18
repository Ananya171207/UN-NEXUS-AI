"""Response schemas for SDG signals, regions, summary and map. camelCase = frontend contract."""
from typing import Any

from pydantic import BaseModel, Field


# ---------- SDG signals ----------
class SDGSignal(BaseModel):
    indicatorKey: str
    indicatorName: str | None = Field(None, description="The World Bank's name for the indicator.")
    indicatorCode: str | None = Field(None, description="World Bank indicator code.")
    value: float | None = Field(None, description="Latest available value. Null unless availability is 'available'.")
    year: str | None = Field(None, description="Year of that value. Years differ between indicators.")
    unit: str | None = None
    source: str | None = None
    availability: str = Field(description="available | no_data | error | pending")
    stale: bool = Field(False, description="True when an older cached value is served because refreshing failed.")
    outdated: bool = Field(False, description="True when the value's year is older than `outdatedAfterYears`.")
    relation: str = Field(description="'matches_sdg_indicator' (same measure as an official UN SDG indicator) or 'related_context'.")
    sdgIndicator: str | None = Field(None, description="Official UN SDG indicator number when relation = matches_sdg_indicator, e.g. '1.1.1'.")
    explanation: str = Field(description="Plain-language description of what the indicator measures.")
    fetchedAt: str | None = None
    error: str | None = None


class SDGGoal(BaseModel):
    sdg: int
    name: str
    signals: list[SDGSignal]
    availableCount: int
    totalCount: int
    hasData: bool


class CountrySDGSignalsOut(BaseModel):
    countryId: str
    countryCode: str
    countryName: str
    dataType: str = Field(description="Always 'indicator_values': real data, not progress scores.")
    aiGenerated: bool = Field(description="Always false: nothing on this endpoint is AI-generated.")
    source: str
    methodology: str
    goals: list[SDGGoal]
    goalsWithoutIndicators: list[int] = Field(description="Goals for which the backend has no indicator (not 'no progress').")
    outdatedAfterYears: int


# ---------- Regions ----------
class RegionEventBrief(BaseModel):
    id: str
    title: str
    severity: str
    category: str
    countryId: str | None = None
    countryName: str | None = None
    occurredAt: str
    url: str | None = None


class RegionOut(BaseModel):
    region: str
    total: int
    critical: int
    high: int
    moderate: int = Field(description="Medium severity (the backend calls it 'moderate').")
    low: int
    countryCount: int
    countryCodes: list[str] = Field(description="ISO alpha-2 ids of countries with events in this region.")
    highestSeverity: str | None = None
    topEvents: list[RegionEventBrief]


class RegionTotals(BaseModel):
    events: int
    withRegion: int
    withoutRegion: int
    regionsWithEvents: int


class RegionsOut(BaseModel):
    regions: list[RegionOut]
    totals: RegionTotals
    assignmentRule: str


# ---------- Summary ----------
class CountOf(BaseModel):
    value: int
    of: int


class SeverityCounts(BaseModel):
    critical: int
    high: int
    moderate: int
    low: int


class SummaryOut(BaseModel):
    countriesInView: CountOf
    eventsShown: int
    highCriticalEvents: int
    regionsWithEvents: CountOf
    severityBreakdown: SeverityCounts
    categoryBreakdown: dict[str, int]
    unmappedEvents: int = Field(description="Matching events with no reliable country (global/unknown).")
    filters: dict[str, Any]
    definitions: dict[str, str]
    warnings: list[str]
    generatedAt: str


# ---------- Map ----------
class EventMarker(BaseModel):
    eventId: str
    title: str
    latitude: float
    longitude: float
    precision: str = Field(description="'city': a named city after a place word. Event-level markers are never country centres.")
    city: str | None = None
    countryId: str
    countryCode: str | None = None
    countryName: str | None = None
    region: str | None = None
    monitoringRegion: str | None = None
    category: str
    severity: str
    occurredAt: str
    url: str | None = None
    locationConfidence: str | None = None
    evidence: list[dict[str, Any]] = []


class CountryMarker(BaseModel):
    countryId: str
    countryCode: str
    countryName: str
    region: str | None = None
    monitoringRegion: str | None = None
    latitude: float
    longitude: float
    coordinatesMean: str = Field(description="Always 'country_centre': not the event location.")
    eventCount: int
    highestSeverity: str | None = None
    severityCounts: SeverityCounts
    eventIds: list[str]


class MapTotals(BaseModel):
    events: int
    eventMarkers: int
    eventsWithoutCoordinates: int
    eventsWithoutCountry: int
    countriesWithoutPosition: int
    invalidCoordinatesDropped: int


class MapOut(BaseModel):
    markers: list[EventMarker]
    countryMarkers: list[CountryMarker]
    totals: MapTotals
    note: str
