from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from db import Base


def utc_now():
    return datetime.now(timezone.utc)


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    nif = Column(String(30), unique=True, nullable=False)
    country_code = Column(String(5), default="ES")
    sector_cnae = Column(String(50), nullable=False)
    employees = Column(Integer, nullable=False)
    turnover_eur = Column(Float, nullable=False)
    total_assets_eur = Column(Float, default=0.0)
    is_public_interest_entity = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)

    emissions = relationship("EmissionRecord", back_populates="company", cascade="all, delete-orphan")
    cbam_imports = relationship("CBAMImport", back_populates="company", cascade="all, delete-orphan")
    taxonomy_activities = relationship("TaxonomyActivity", back_populates="company", cascade="all, delete-orphan")
    ict_metrics = relationship("ICTSustainabilityRecord", back_populates="company", cascade="all, delete-orphan")
    dpps = relationship("DigitalProductPassport", back_populates="company", cascade="all, delete-orphan")
    dma_assessments = relationship("DMAAssessment", back_populates="company", cascade="all, delete-orphan")
    dnsh_assessments = relationship("DNSHAssessment", back_populates="company", cascade="all, delete-orphan")


class EmissionFactorVersion(Base):
    __tablename__ = "emission_factor_versions"

    id = Column(Integer, primary_key=True, index=True)
    year = Column(Integer, nullable=False, index=True)
    activity_key = Column(String(100), nullable=False, index=True)
    factor_kg_co2e = Column(Float, nullable=False)
    source = Column(String(150), default="MITECO/OECC 2026")
    version_tag = Column(String(50), default="v2026.05")


class EmissionRecord(Base):
    __tablename__ = "emission_records"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    reporting_year = Column(Integer, nullable=False)
    country_code = Column(String(5), default="ES")  # Segmentación Registro MITECO vs CSRD global
    scope = Column(Integer, nullable=False)  # 1, 2 o 3
    activity_key = Column(String(100), nullable=False)
    activity_amount = Column(Float, nullable=False)
    unit = Column(String(30), nullable=False)
    has_gdo_certificate = Column(Boolean, default=False)
    evidence_ref = Column(String(255), nullable=True)  # Factura / Certificado GdO
    factor_version = Column(String(50), nullable=False)
    tco2e_location_based = Column(Float, nullable=False)
    tco2e_market_based = Column(Float, nullable=False)
    created_at = Column(DateTime, default=utc_now)

    company = relationship("Company", back_populates="emissions")


class CBAMImport(Base):
    __tablename__ = "cbam_imports"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    reporting_year = Column(Integer, nullable=False)
    quarter = Column(String(10), nullable=False)  # ej. "2026-Q3"
    cn_code = Column(String(20), nullable=False)
    sector = Column(String(50), nullable=False)
    origin_country = Column(String(50), nullable=False)
    net_mass_tonnes = Column(Float, nullable=False)
    is_verified_actual = Column(Boolean, default=False)
    see_input_tco2e_t = Column(Float, nullable=False)
    effective_see_tco2e_t = Column(Float, nullable=False)
    benchmark_tco2e_t = Column(Float, nullable=False)
    free_allocation_factor = Column(Float, nullable=False)
    art9_deduction_certs = Column(Float, default=0.0)
    ets_price_eur = Column(Float, nullable=False)
    certificates_required = Column(Float, nullable=False)
    estimated_cost_eur = Column(Float, nullable=False)
    taric_code = Column(String(10), nullable=False)  # Y128, Y137, Y238
    created_at = Column(DateTime, default=utc_now)

    company = relationship("Company", back_populates="cbam_imports")


class TaxonomyActivity(Base):
    __tablename__ = "taxonomy_activities"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    reporting_year = Column(Integer, nullable=False)
    activity_name = Column(String(200), nullable=False)
    turnover_eur = Column(Float, default=0.0)
    capex_eur = Column(Float, default=0.0)
    opex_eur = Column(Float, default=0.0)
    is_eligible = Column(Boolean, default=False)
    is_aligned = Column(Boolean, default=False)
    dnsh_compliant = Column(Boolean, default=False)
    min_safeguards_compliant = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)

    company = relationship("Company", back_populates="taxonomy_activities")


class ICTSustainabilityRecord(Base):
    __tablename__ = "ict_sustainability_records"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    facility_name = Column(String(150), nullable=False)
    installed_it_power_kw = Column(Float, nullable=False)
    nominal_energy_input_mw = Column(Float, default=0.0)
    e_dc_kwh = Column(Float, nullable=False)
    e_it_kwh = Column(Float, nullable=False)
    w_in_m3 = Column(Float, nullable=False)
    e_reuse_kwh = Column(Float, default=0.0)
    e_res_tot_kwh = Column(Float, default=0.0)
    pue = Column(Float, nullable=False)
    wue = Column(Float, nullable=False)
    erf = Column(Float, nullable=False)
    ref = Column(Float, nullable=False)
    waste_heat_alert = Column(Boolean, default=False)
    # ISO/IEC 21031:2024 (SCI)
    sw_energy_kwh = Column(Float, default=0.0)
    grid_intensity_gco2_kwh = Column(Float, default=258.0)
    embodied_hardware_gco2 = Column(Float, default=0.0)
    functional_units = Column(Float, default=1.0)
    sci_gco2_per_unit = Column(Float, default=0.0)
    created_at = Column(DateTime, default=utc_now)

    company = relationship("Company", back_populates="ict_metrics")


class DigitalProductPassport(Base):
    __tablename__ = "digital_product_passports"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    gtin = Column(String(30), nullable=False)
    serial_number = Column(String(100), unique=True, nullable=False)
    product_name = Column(String(200), nullable=False)
    category = Column(String(100), nullable=False)  # baterias, acero, textil, aluminio, mobiliario
    pef_carbon_footprint_kgco2e = Column(Float, nullable=False)
    total_mass_kg = Column(Float, nullable=False)
    recycled_content_kg = Column(Float, default=0.0)
    waste_diverted_pct = Column(Float, default=0.0)
    repairability_score = Column(Float, default=0.0)  # 0 a 10
    gs1_digital_link = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=utc_now)

    company = relationship("Company", back_populates="dpps")


class DMAAssessment(Base):
    __tablename__ = "dma_assessments"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    stage = Column(String(10), nullable=False)  # T0, T1, T2
    d1_strategy = Column(Float, nullable=False)
    d2_readiness = Column(Float, nullable=False)
    d3_human_centric = Column(Float, nullable=False)
    d4_data_security = Column(Float, nullable=False)
    d5_automation_ai = Column(Float, nullable=False)
    d6_green_digital = Column(Float, nullable=False)
    overall_score = Column(Float, nullable=False)
    maturity_level = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=utc_now)

    company = relationship("Company", back_populates="dma_assessments")


class DNSHAssessment(Base):
    __tablename__ = "dnsh_assessments"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    project_name = Column(String(200), nullable=False)
    intervention_field_code = Column(String(20), default="021ter")
    climate_tag_pct = Column(Integer, default=40)
    digital_tag_pct = Column(Integer, default=100)
    obj1_mitigation_ok = Column(Boolean, default=True)
    obj2_adaptation_ok = Column(Boolean, default=True)
    obj3_water_ok = Column(Boolean, default=True)
    obj4_circular_ok = Column(Boolean, default=True)
    obj5_pollution_ok = Column(Boolean, default=True)
    obj6_biodiversity_ok = Column(Boolean, default=True)
    overall_compliant = Column(Boolean, default=True)
    evidence_notes = Column(Text, default="")
    created_at = Column(DateTime, default=utc_now)

    company = relationship("Company", back_populates="dnsh_assessments")


class GDPRConsent(Base):
    __tablename__ = "gdpr_consents"

    id = Column(Integer, primary_key=True, index=True)
    subject_hash = Column(String(64), nullable=False)  # Identificador anonimizado SHA-256
    purpose = Column(String(200), nullable=False)
    granted = Column(Boolean, default=True)
    legal_basis = Column(String(100), default="Consentimiento explícito RGPD Art. 6.1.a")
    recorded_at = Column(DateTime, default=utc_now)


class CRAVulnerabilityIncident(Base):
    __tablename__ = "cra_vulnerability_incidents"

    id = Column(Integer, primary_key=True, index=True)
    cve_id = Column(String(40), nullable=False)
    component_name = Column(String(120), nullable=False)
    actively_exploited = Column(Boolean, default=True)
    detected_at = Column(DateTime, default=utc_now)
    enisa_deadline_24h = Column(DateTime, nullable=False)
    status = Column(String(50), default="PENDIENTE_NOTIFICACION_ENISA")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=utc_now)
    module = Column(String(80), nullable=False)
    action = Column(String(100), nullable=False)
    payload_json = Column(Text, nullable=False)
    previous_hash = Column(String(64), nullable=False)
    record_hash = Column(String(64), nullable=False, unique=True)