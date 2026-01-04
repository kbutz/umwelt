from pydantic import BaseModel, Field, field_validator, ValidationInfo
from typing import List, Optional, Literal

# --- Sub-Models ---

class Taxonomy(BaseModel):
    class_: str = Field(..., alias="class", description="Biological Class (e.g., Mammalia)")
    order: str = Field(..., description="Biological Order (e.g., Chiroptera)")

class Identity(BaseModel):
    common_name: str
    scientific_name: str
    taxonomy: Taxonomy

class QuantitativeData(BaseModel):
    min: Optional[float] = Field(None, description="Minimum threshold value")
    max: Optional[float] = Field(None, description="Maximum threshold value")
    unit: Optional[str] = Field(None, description="Measurement unit (e.g., Hz, nm, uV/cm)")
    context: Optional[str] = Field(None, description="Context of measurement (e.g., 'Physiological Limit')")

    @field_validator('max')
    def check_min_max(cls, v, info: ValidationInfo):
        values = info.data
        if v is not None and values.get('min') is not None:
            if v < values['min']:
                raise ValueError(f"Max value ({v}) cannot be less than Min value ({values['min']})")
        return v

class Mechanism(BaseModel):
    level: Literal['Anatomical', 'Cellular', 'Neural', 'Genetic', 'Behavioral', 'Physiological', 'Unknown']
    description: str

class Evidence(BaseModel):
    source_type: str = Field(..., description="Type of source (e.g., 'Behavioral Audiogram', 'Review Paper', 'Primary Study')")
    source_name: str = Field(..., description="Name of the source (e.g., 'Wikipedia', 'Nature Journal', 'Journal of Experimental Biology')")
    url: Optional[str] = Field(None, description="Direct URL to the source")
    title: Optional[str] = Field(None, description="Title of the paper or article")
    author: Optional[str] = Field(None, description="Lead author or organization")
    year: Optional[int] = Field(None, description="Year of publication")
    citation: str = Field(..., description="Full academic citation or summary reference")
    note: Optional[str] = None

class SensoryModality(BaseModel):
    modality_domain: Literal['Mechanoreception', 'Chemoreception', 'Photoreception', 'Electroreception', 'Magnetoreception', 'Thermoreception', 'Other']
    sub_type: str = Field(..., description="Specific sense (e.g., 'Echolocation', 'UV Vision')")
    stimulus_type: str = Field(..., description="Physical stimulus (e.g., 'Pressure Wave')")

    # Optional fields (The "Null Protocol")
    quantitative_data: Optional[QuantitativeData] = None
    mechanism: Optional[Mechanism] = None
    evidence: List[Evidence] = Field(default_factory=list)

class DataQualityMeta(BaseModel):
    data_quality_flag: Literal['High_Evidence', 'Inferred_Only', 'Contested', 'Low_Data']

# --- The Root Model ---

class AnimalSensoryData(BaseModel):
    identity: Identity
    sensory_modalities: List[SensoryModality]
    meta: DataQualityMeta
