"""Response schemas for the India vs World endpoints (`/api/compare`, `/api/compare/indicators`).

Every model allows extra fields, so a field added by the service later is passed through
to the client instead of being silently dropped by `response_model` filtering.
"""
from pydantic import BaseModel, ConfigDict, Field


class _Open(BaseModel):
    model_config = ConfigDict(extra="allow")


class IndicatorValue(_Open):
    """One indicator for one country. `year` and `value` keep the shape the original /api/compare returned."""
    key: str
    value: float | int | None = Field(None, description="Latest World Bank value. Null when unavailable, never estimated.")
    year: str | None = Field(None, description="Reporting year of `value`.")
    label: str
    unit: str
    group: str = Field(description="economic | social | environmental")
    source: str
    sourceCode: str = Field(description="World Bank indicator code.")
    indicatorName: str | None = Field(None, description="The World Bank's own name for the indicator.")
    status: str = Field(description="available | no_data | error | pending")
    stale: bool = Field(False, description="True when a failed refresh was answered from the last good cached value.")
    error: str | None = None
    sourceLastUpdated: str | None = None
    fetchedAt: str | None = None


class BaselineInfo(_Open):
    country: str = Field(description="ISO alpha-3 code of the baseline country.")
    name: str
    basis: str = Field(description="default_india | requested | first_country")


class CountryMetadata(_Open):
    id: str = Field(description="ISO alpha-2.")
    code: str = Field(description="ISO alpha-3.")
    alpha2: str
    alpha3: str
    name: str
    region: str | None = None
    subregion: str | None = None
    capital: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    position: list[float] | None = None
    flag: str | None = Field(None, description="Flag image URL.")
    flagEmoji: str | None = None
    metadataSource: str | None = None
    isBaseline: bool = False


class IndicatorFormat(_Open):
    kind: str = Field(description="currency | count | percent | years | tonnes_per_capita | concentration | number")
    decimals: int
    prefix: str = ""
    suffix: str = ""
    compact: bool = Field(False, description="True when values are large enough to be shown as 1.2T / 1.4B.")


class IndicatorChartHints(_Open):
    axisLabel: str
    canBeNegative: bool
    recommendedChart: str


class IndicatorMetadata(_Open):
    key: str
    label: str
    unit: str
    category: str = Field(description="economic | social | environmental")
    worldBankCode: str
    sdgs: list[int] = Field(default_factory=list, description="SDGs the indicator relates to (empty when none is mapped).")
    source: str
    direction: str = Field(description="higher_is_better | lower_is_better | contextual")
    interpretation: str | None = Field(None, description="How to read a difference, and its limits.")
    differenceUnit: str = Field(description="Unit of an absolute difference (percentage points for % indicators).")
    format: IndicatorFormat
    chart: IndicatorChartHints


class CategoryInfo(_Open):
    id: str
    label: str
    indicatorKeys: list[str]


class IndicatorCatalogueResponse(_Open):
    source: str
    count: int
    categories: list[CategoryInfo]
    indicators: list[IndicatorMetadata]


class CoverageInfo(_Open):
    requested: int
    available: int
    ratio: float
    countriesWithData: list[str]
    countriesMissing: list[dict]


class HighLow(_Open):
    country: str
    value: float | int
    year: str | None = None
    tie: bool = Field(False, description="True when another selected country has exactly the same value.")


class CountryIndicatorComparison(_Open):
    country: str
    value: float | int | None = None
    year: str | None = None
    status: str
    stale: bool = False
    usable: bool = Field(description="False when the value is missing or invalid and therefore excluded from every calculation.")
    reason: str | None = Field(None, description="Why the value is unusable: no_data | error | pending | invalid_value | unit_mismatch.")
    isBaseline: bool = False
    absoluteDifference: float | int | None = Field(None, description="value - baseline value, in `differenceUnit`.")
    percentDifference: float | None = Field(None, description="(value - baseline) / |baseline| * 100. Null when the baseline is zero or missing.")
    percentDifferenceNote: str | None = Field(None, description="Why `percentDifference` is null: baseline_is_zero | baseline_unavailable | value_unavailable.")
    yearDifference: int | None = Field(None, description="Reporting year minus the baseline's reporting year.")
    comparedWithBaseline: str | None = Field(None, description="higher | lower | equal")
    performanceVsBaseline: str | None = Field(None, description="better | worse | same. Null for contextual indicators.")
    valueRank: int | None = Field(None, description="1 = highest value among the selected countries (ties share a rank).")
    performanceRank: int | None = Field(None, description="1 = best among the selected countries. Null for contextual indicators.")


class IndicatorAnalytics(_Open):
    key: str
    label: str
    unit: str
    group: str
    direction: str
    differenceUnit: str
    comparable: bool = Field(description="True when at least two selected countries have a usable value.")
    baseline: dict
    values: list[CountryIndicatorComparison]
    orderedByValue: list[str] = Field(description="Country codes, highest value first. Says nothing about which is better.")
    orderedBestToWorst: list[str] | None = Field(None, description="Only for directional indicators.")
    highest: HighLow | None = None
    lowest: HighLow | None = None
    coverage: CoverageInfo
    years: dict[str, str | None]
    yearsDiffer: bool
    notes: list[str] = Field(default_factory=list)


class CountryDataQuality(_Open):
    total: int
    available: int
    noData: int
    error: int
    pending: int
    stale: int
    coverage: float = Field(description="available / total, 0 to 1.")
    complete: bool
    staleIndicators: list[str]
    missing: list[dict] = Field(description="Every unavailable indicator: {key, status, reason}.")


class ComparisonResponse(_Open):
    source: str
    comparison: dict[str, dict[str, IndicatorValue]] = Field(
        description="ISO alpha-3 -> indicator key -> value. Backward compatible with the original endpoint.")
    countries: list[str] = Field(description="ISO alpha-3 codes in the requested order, duplicates removed.")
    baseline: BaselineInfo
    countryMetadata: dict[str, CountryMetadata]
    indicatorMetadata: list[IndicatorMetadata]
    analytics: dict[str, IndicatorAnalytics]
    dataQuality: dict[str, CountryDataQuality]
    dataStatus: str = Field(description="complete | partial")
    warnings: list[str]
    lastUpdated: str | None = None
