from typing import Optional
from pydantic import BaseModel, Field


class EmissionCreate(BaseModel):
    company_id: int = 1
    reporting_year: int = Field(2025, ge=2007, le=2035)
    country_code: str = Field("ES", min_length=2, max_length=5)
    scope: int = Field(..., ge=1, le=3)
    activity_key: str
    activity_amount: float = Field(..., gt=0)
    unit: str = "kWh"
    has_gdo_certificate: bool = False
    evidence_ref: Optional[str] = None


class CBAMImportCreate(BaseModel):
    company_id: int = 1
    reporting_year: int = Field(2026, ge=2026, le=2034)
    quarter: str = "2026-Q3"
    cn_code: str = "2523 10 00"
    sector: str = "cemento"
    origin_country: str = "Turquía"
    net_mass_tonnes: float = Field(..., gt=0)
    is_verified_actual: bool = False
    see_input_tco2e_t: Optional[float] = None
    art9_deduction_certs: float = Field(0.0, ge=0)


class TaxonomyActivityCreate(BaseModel):
    company_id: int = 1
    reporting_year: int = 2026
    activity_name: str
    turnover_eur: float = Field(0.0, ge=0)
    capex_eur: float = Field(0.0, ge=0)
    opex_eur: float = Field(0.0, ge=0)
    is_eligible: bool = True
    is_aligned: bool = True
    dnsh_compliant: bool = True
    min_safeguards_compliant: bool = True


class ICTSustainabilityCreate(BaseModel):
    company_id: int = 1
    facility_name: str
    installed_it_power_kw: float = Field(..., gt=0)
    nominal_energy_input_mw: float = Field(0.0, ge=0)
    e_dc_kwh: float = Field(..., gt=0)
    e_it_kwh: float = Field(..., gt=0)
    w_in_m3: float = Field(..., ge=0)
    e_reuse_kwh: float = Field(0.0, ge=0)
    e_res_tot_kwh: float = Field(0.0, ge=0)
    sw_energy_kwh: float = Field(0.0, ge=0)
    grid_intensity_gco2_kwh: float = Field(258.0, ge=0)
    embodied_hardware_gco2: float = Field(0.0, ge=0)
    functional_units: float = Field(1.0, gt=0)


class DPPCreate(BaseModel):
    company_id: int = 1
    gtin: str = Field(..., min_length=8, max_length=14)
    serial_number: str
    product_name: str
    category: str = "acero"
    pef_carbon_footprint_kgco2e: float = Field(..., ge=0)
    total_mass_kg: float = Field(..., gt=0)
    recycled_content_kg: float = Field(0.0, ge=0)
    waste_diverted_pct: float = Field(85.0, ge=0, le=100)
    repairability_score: float = Field(8.0, ge=0, le=10)


class DMACreate(BaseModel):
    company_id: int = 1
    stage: str = Field("T0", pattern="^(T0|T1|T2)$")
    d1_strategy: float = Field(..., ge=0, le=100)
    d2_readiness: float = Field(..., ge=0, le=100)
    d3_human_centric: float = Field(..., ge=0, le=100)
    d4_data_security: float = Field(..., ge=0, le=100)
    d5_automation_ai: float = Field(..., ge=0, le=100)
    d6_green_digital: float = Field(..., ge=0, le=100)


class DNSHCreate(BaseModel):
    company_id: int = 1
    project_name: str
    intervention_field_code: str = "021ter"
    climate_tag_pct: int = Field(40, ge=0, le=100)
    digital_tag_pct: int = Field(100, ge=0, le=100)
    obj1_mitigation_ok: bool = True
    obj2_adaptation_ok: bool = True
    obj3_water_ok: bool = True
    obj4_circular_ok: bool = True
    obj5_pollution_ok: bool = True
    obj6_biodiversity_ok: bool = True
    evidence_notes: str = ""


class GDPRConsentCreate(BaseModel):
    subject_identifier: str
    purpose: str
    granted: bool = True


class CRAIncidentCreate(BaseModel):
    cve_id: str
    component_name: str
    actively_exploited: bool = True