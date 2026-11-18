"""Response schema for the country list (frontend shape plus extras)."""
from pydantic import BaseModel, Field


class CountryIndicators(BaseModel):
    lifeExpectancy: float | None = Field(None, description="years")
    renewableShare: float | None = Field(None, description="% of electricity output")
    internetUse: float | None = Field(None, description="% of population")


class CountryOut(BaseModel):
    id: str = Field(description="ISO alpha-2. The id the frontend and events use.")
    code: str = Field(description="ISO alpha-3 (the `code` of the original endpoint).")
    name: str
    region: str | None = Field(None, description="Asia, Europe, Africa, North America, South America or Oceania.")
    subregion: str | None = Field(None, description="UN sub-region, e.g. 'Southern Asia', 'Western Asia'.")
    capital: str | None = None
    position: list[float] | None = Field(None, description="[latitude, longitude] of the country's centre. Null if unknown.")
    latitude: float | None = None
    longitude: float | None = None
    flag: str | None = Field(None, description="Flag image URL.")
    flagEmoji: str | None = None
    populationM: float | None = Field(None, description="Population in millions (World Bank). Null if unavailable.")
    gdpB: float | None = Field(None, description="GDP in billions of current US$ (World Bank). Null if unavailable.")
    indicators: CountryIndicators
    dataYears: dict[str, str | None] = Field(description="Year of each World Bank value above.")
    metadataSource: str
