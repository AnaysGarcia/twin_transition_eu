import csv
import io
import uuid
from datetime import datetime, timezone
from typing import Any, Dict
from sqlalchemy.orm import Session

import config
import engines
import models


def export_vsme_report(db: Session , company: models.Company) -> Dict[str, Any]:
    """Exportación estructurada mapeada al estándar voluntario EFRAG VSME (preparada para conversor Inline XBRL)."""
    s1 = sum(e.tco2e_location_based for e in company.emissions if e.scope == 1)
    s2_loc = sum(e.tco2e_location_based for e in company.emissions if e.scope == 2)
    s2_mkt = sum(e.tco2e_market_based for e in company.emissions if e.scope == 2)
    s3 = sum(e.tco2e_location_based for e in company.emissions if e.scope == 3)
    es_s1_s2 = sum(e.tco2e_market_based for e in company.emissions if e.country_code == "ES" and e.scope in (1, 2))
    taxonomy = engines.calculate_taxonomy_kpis(company.taxonomy_activities)

    return {
        "schema": "EFRAG-VSME-2026-XBRL-READY",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "entity": {
            "name": company.name,
            "nif": company.nif,
            "country": company.country_code,
            "employees": company.employees,
            "turnover_eur": company.turnover_eur,
            "regulatory_classification": engines.classify_company_obligations(company),
        },
        "B3_energy_and_ghg_emissions": {
            "scope_1_tco2e": round(s1, 4),
            "scope_2_location_based_tco2e": round(s2_loc, 4),
            "scope_2_market_based_tco2e": round(s2_mkt, 4),
            "scope_3_tco2e": round(s3, 4),
            "spain_rd214_2025_scope1_2_tco2e": round(es_s1_s2, 4),
            "ghg_intensity_tco2e_per_meur": round(((s1 + s2_mkt) / (company.turnover_eur / 1_000_000)), 4) if company.turnover_eur > 0 else 0.0,
        },
        "eu_taxonomy_2026_73": taxonomy,
        "audit_chain_status": engines.verify_audit_chain(db),
    }


def export_dpp_jsonld(dpp: models.DigitalProductPassport , company: models.Company) -> Dict[str, Any]:
    """Pasaporte Digital de Producto JSON-LD alineado con ESPR (Reg. 2024/1781) y normas EN 18216-18223."""
    recycled_pct = round((dpp.recycled_content_kg / dpp.total_mass_kg) * 100.0, 2)
    return {
        "@context": [
            "https://www.w3.org/2018/credentials/v1",
            "https://vocabulary.uncefact.org/dpp-context-2026.jsonld",
        ],
        "id": dpp.gs1_digital_link,
        "type": ["DigitalProductPassport", "EU_ESPR_2024_1781"],
        "standards": ["EN 18216", "EN 18219", "EN 18220", "ISO/IEC 15459"],
        "economicOperator": {"name": company.name, "vatId": company.nif, "country": company.country_code},
        "product": {
            "name": dpp.product_name,
            "category": dpp.category,
            "gtin": dpp.gtin,
            "serialNumber": dpp.serial_number,
        },
        "environmentalFootprint_PEF_EF31": {
            "carbonFootprint_kgCO2e": dpp.pef_carbon_footprint_kgco2e,
            "method": "EU PEF / EF 3.1 (ISO 14040/14044)",
        },
        "circularity_ESRS_E5": {
            "totalMass_kg": dpp.total_mass_kg,
            "recycledContent_kg": dpp.recycled_content_kg,
            "recycledContent_pct": recycled_pct,
            "wasteDivertedFromLandfill_pct": dpp.waste_diverted_pct,
            "repairabilityIndex_0_10": dpp.repairability_score,
        },
        "accessControl": {"publicLayer": True, "authorityRegistrySynced": "EU-Central-DPP-Registry-2026"},
    }


def export_cbam_declaration(company: models.Company) -> Dict[str, Any]:
    """Declaración anual CBAM estructurada para Registro CBAM (DG TAXUD / MITECO / AEAT)."""
    total_mass = sum(i.net_mass_tonnes for i in company.cbam_imports)
    total_certs = sum(i.certificates_required for i in company.cbam_imports)
    total_cost = sum(i.estimated_cost_eur for i in company.cbam_imports)
    return {
        "regulation": "EU CBAM Definitive Phase (Reg. 2023/956 & Reg. 2025/2083)",
        "declarant": {"name": company.name, "nif": company.nif, "national_authority_es": "MITECO (OECC) / AEAT"},
        "summary": {
            "total_net_mass_tonnes": round(total_mass, 3),
            "threshold_50t_exceeded": total_mass > config.CBAM_MASS_THRESHOLD_TONNES,
            "total_certificates_to_surrender": round(total_certs, 5),
            "quarterly_holding_requirement_50pct": round(total_certs * 0.50, 5),
            "total_estimated_cost_eur": round(total_cost, 2),
        },
        "goods_imported": [
            {
                "quarter": i.quarter,
                "cn_code": i.cn_code,
                "sector": i.sector,
                "origin_country": i.origin_country,
                "net_mass_tonnes": i.net_mass_tonnes,
                "data_type": "VERIFIED_ACTUAL" if i.is_verified_actual else "DEFAULT_WITH_MARKUP",
                "effective_see_tco2e_t": i.effective_see_tco2e_t,
                "benchmark_tco2e_t": i.benchmark_tco2e_t,
                "free_allocation_factor": i.free_allocation_factor,
                "taric_code": i.taric_code,
                "certificates_required": i.certificates_required,
                "estimated_cost_eur": i.estimated_cost_eur,
            }
            for i in company.cbam_imports
        ],
    }


def export_sbom_cyclonedx() -> Dict[str, Any]:
    """Genera un SBOM en formato estándar CycloneDX 1.5 exigido por el Cyber Resilience Act (Reg. 2024/2847)."""
    components = [
        {"type": "library", "name": "fastapi", "version": "0.115.x", "purl": "pkg:pypi/fastapi@0.115.0"},
        {"type": "library", "name": "uvicorn", "version": "0.32.x", "purl": "pkg:pypi/uvicorn@0.32.0"},
        {"type": "library", "name": "sqlalchemy", "version": "2.0.x", "purl": "pkg:pypi/sqlalchemy@2.0.35"},
        {"type": "library", "name": "pydantic", "version": "2.9.x", "purl": "pkg:pypi/pydantic@2.9.0"},
        {"type": "library", "name": "jinja2", "version": "3.1.x", "purl": "pkg:pypi/jinja2@3.1.4"},
    ]
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": f"urn:uuid:{uuid.uuid4()}",
        "version": 1,
        "metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "component": {
                "type": "application",
                "name": config.APP_NAME,
                "version": config.APP_VERSION,
            },
            "properties": [
                {"name": "eu:regulation", "value": "Cyber Resilience Act (EU) 2024/2847"},
                {"name": "eu:vulnerability_reporting_sla", "value": "24h ENISA Early Warning"},
            ],
        },
        "components": components,
    }


def export_dma_csv(company: models.Company) -> str:
    """Genera exportación CSV compatible con carga masiva de la red EDIH (DMA T0/T1/T2)."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Company", "NIF", "Stage", "D1_Strategy", "D2_Readiness", "D3_HumanCentric",
        "D4_DataSecurity", "D5_AutomationAI", "D6_GreenDigital", "OverallScore", "MaturityLevel"
    ])
    for d in company.dma_assessments:
        writer.writerow([
            company.name, company.nif, d.stage, d.d1_strategy, d.d2_readiness,
            d.d3_human_centric, d.d4_data_security, d.d5_automation_ai,
            d.d6_green_digital, d.overall_score, d.maturity_level
        ])
    return output.getvalue()


def export_data_act_portability(db: Session , company: models.Company) -> Dict[str, Any]:
    """Paquete de portabilidad total sin vendor lock-in (Data Act Cap. VI y derecho de portabilidad RGPD ARSULIPO)."""
    return {
        "standard": "EU Data Act (Reg. 2023/2854 Ch. VI) & RGPD Art. 20 Portability Package",
        "dataspace_protocol": "IDSA DSP 2025-1 / Eclipse EDC ODRL-ready",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "vsme_esg": export_vsme_report(db, company),
        "cbam": export_cbam_declaration(company),
        "dpps": [export_dpp_jsonld(p, company) for p in company.dpps],
        "dnsh_projects": [
            {
                "project_name": p.project_name,
                "intervention_field": p.intervention_field_code,
                "climate_tag_pct": p.climate_tag_pct,
                "digital_tag_pct": p.digital_tag_pct,
                "overall_compliant": p.overall_compliant,
            }
            for p in company.dnsh_assessments
        ],
    }