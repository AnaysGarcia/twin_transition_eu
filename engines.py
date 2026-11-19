import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Tuple
from sqlalchemy.orm import Session

import config
import models


# =====================================================================
# MOTOR TRANSVERSAL: CADENA DE AUDITORÍA INMUTABLE (SHA-256)
# =====================================================================
def record_audit(db: Session, module: str, action: str, payload: Dict[str, Any]) -> models.AuditLog:
    last_log = db.query(models.AuditLog).order_by(models.AuditLog.id.desc()).first()
    prev_hash = last_log.record_hash if last_log else "GENESIS_TWIN_TRANSITION_EU_2026"
    now = datetime.now(timezone.utc)
    payload_str = json.dumps(payload, sort_keys=True, default=str)
    raw = f"{prev_hash}|{now.isoformat()}|{module}|{action}|{payload_str}"
    rec_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()

    entry = models.AuditLog(
        timestamp=now,
        module=module,
        action=action,
        payload_json=payload_str,
        previous_hash=prev_hash,
        record_hash=rec_hash,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def verify_audit_chain(db: Session) -> Dict[str, Any]:
    logs = db.query(models.AuditLog).order_by(models.AuditLog.id.asc()).all()
    expected_prev = "GENESIS_TWIN_TRANSITION_EU_2026"
    for log in logs:
        if log.previous_hash != expected_prev:
            return {"valid": False, "broken_at_id": log.id, "total_records": len(logs)}
        expected_prev = log.record_hash
    return {"valid": True, "total_records": len(logs), "last_hash": expected_prev}


# =====================================================================
# MOTOR 1: HUELLA DE CARBONO CORPORATIVA (GHG, ESRS E1 y RD 214/2025)
# =====================================================================
def calculate_carbon_emission(
    db: Session,
    year: int,
    scope: int,
    activity_key: str,
    activity_amount: float,
    has_gdo_certificate: bool,
    evidence_ref: str | None,
) -> Tuple[float, float, str, str | None]:
    """
    Calcula tCO2e simultáneamente en location-based y market-based.
    Bloquea factor renovable 0.0 si no existe certificado GdO respaldado por evidencia documental.
    """
    factor_row = (
        db.query(models.EmissionFactorVersion)
        .filter_by(year=year, activity_key=activity_key)
        .first()
    )
    if factor_row:
        base_factor = factor_row.factor_kg_co2e
        version_tag = f"{factor_row.source} ({factor_row.version_tag} - {year})"
    else:
        year_factors = config.MITECO_FACTORS.get(year , config.MITECO_FACTORS[2025])
        base_factor = year_factors.get(activity_key, 0.258)
        version_tag = f"MITECO-Fallback ({year})"

    location_based = round((activity_amount * base_factor) / 1000.0, 6)

    warning = None
    if scope == 2 and "electricidad" in activity_key:
        if has_gdo_certificate and evidence_ref and evidence_ref.strip():
            market_based = 0.0
        elif has_gdo_certificate:
            # Regla anti-greenwashing / auditoría: sin referencia documental, no aplica factor 0
            market_based = location_based
            warning = "GdO marcada sin referencia documental: aplicado mix nacional por defecto."
        else:
            market_based = location_based
    else:
        market_based = location_based

    return location_based, market_based, version_tag, warning


def classify_company_obligations(company: models.Company) -> Dict[str, Any]:
    """Determina obligaciones legales bajo CSRD Ómnibus (Dir. 2026/470) y RD 214/2025."""
    csrd_obligated = (
            company.employees > config.CSRD_MIN_EMPLOYEES
            and company.turnover_eur > config.CSRD_MIN_TURNOVER_EUR
    )
    einf_rd214_obligated = company.employees > 250 and (
        company.is_public_interest_entity
        or company.total_assets_eur > 20_000_000
        or company.turnover_eur > 40_000_000
    )
    return {
        "csrd_obligated": csrd_obligated,
        "recommended_esg_standard": "ESRS Revisados (Reg. Del. 2026/1563)" if csrd_obligated else "Estándar Voluntario VSME (Escudo Cadena de Valor <1.000 empl.)",
        "rd_214_2025_obligated": einf_rd214_obligated,
        "plan_reduccion_5_anos": "Obligatorio (publicación <6 meses tras cierre)" if einf_rd214_obligated else "Voluntario (recomendado para Registro MITECO y licitaciones)",
    }


# =====================================================================
# MOTOR 2: CBAM FASE DEFINITIVA (Reg. 2023/956 + 2025/2083)
# =====================================================================
def calculate_cbam_liability(
    db: Session,
    company_id: int,
    year: int,
    quarter: str,
    cn_code: str,
    sector: str,
    net_mass_tonnes: float,
    is_verified_actual: bool,
    see_input_tco2e_t: float | None,
    art9_deduction_certs: float = 0.0,
) -> Dict[str, Any]:
    bench_info = config.CBAM_BENCHMARKS.get(
        cn_code,
        {"benchmark": 0.666, "default_see": 1.410, "sector": sector},
    )
    benchmark = bench_info["benchmark"]
    base_see = see_input_tco2e_t if see_input_tco2e_t is not None else bench_info["default_see"]

    # Recargo escalonado si se usan valores por defecto (sin verificación acreditada UE)
    if is_verified_actual:
        markup = 0.0
    else:
        markup_group = "fertilizantes" if sector == "fertilizantes" else "general"
        markup_year = min(max(year, 2026), 2028)
        markup = config.CBAM_DEFAULT_MARKUP[markup_group][markup_year]

    effective_see = round(base_see * (1.0 + markup), 6)
    free_alloc = config.CBAM_FREE_ALLOCATION_FACTOR.get(year , 0.975)
    ets_price = config.CBAM_ETS_QUARTERLY_PRICES_2026.get(quarter , 82.32)

    # Comprobar umbral anual acumulado de 50 toneladas (excepto electricidad e hidrógeno)
    existing_mass = sum(
        row.net_mass_tonnes
        for row in db.query(models.CBAMImport)
        .filter_by(company_id=company_id, reporting_year=year)
        .all()
        if row.sector not in ("electricidad", "hidrogeno")
    )
    projected_mass = existing_mass + (0.0 if sector in ("electricidad", "hidrogeno") else net_mass_tonnes)

    if sector not in ("electricidad", "hidrogeno") and projected_mass <= config.CBAM_MASS_THRESHOLD_TONNES:
        taric_code = "Y137"  # Exento por debajo de 50 toneladas netas anuales
        certs = 0.0
        cost = 0.0
    else:
        taric_code = "Y128"  # Declarante Autorizado CBAM
        unit_certs = max(0.0, effective_see - (benchmark * free_alloc))
        certs = round(max(0.0, (net_mass_tonnes * unit_certs) - art9_deduction_certs), 5)
        cost = round(certs * ets_price, 2)

    return {
        "effective_see": effective_see,
        "markup_applied_pct": round(markup * 100, 1),
        "benchmark": benchmark,
        "free_allocation_factor": free_alloc,
        "ets_price_eur": ets_price,
        "certificates_required": certs,
        "estimated_cost_eur": cost,
        "taric_code": taric_code,
        "holding_rule_50pct_certs": round(certs * 0.50, 4),
    }


# =====================================================================
# MOTOR 3: TAXONOMÍA UE (Reg. Del. 2026/73 + Filtro Materialidad 10%)
# =====================================================================
def calculate_taxonomy_kpis(activities: List[models.TaxonomyActivity]) -> Dict[str, Any]:
    def compute_ratio(attr: str) -> Dict[str, Any]:
        total = sum(getattr(a, attr) for a in activities)
        if total <= 0:
            return {"total_eur": 0.0, "aligned_eur": 0.0, "aligned_pct": 0.0, "non_material_excluded": []}

        # Filtro de materialidad del 10%: prioriza excluir actividades no alineadas más pequeñas cuya suma < 10%
        non_aligned = sorted(
            [a for a in activities if not (a.is_aligned and a.dnsh_compliant and a.min_safeguards_compliant)],
            key=lambda x: getattr(x, attr),
        )
        excluded_names = []
        excluded_sum = 0.0
        for act in non_aligned:
            val = getattr(act, attr)
            if ((excluded_sum + val) / total) * 100.0 < config.TAXONOMY_MATERIALITY_LIMIT_PCT:
                excluded_sum += val
                excluded_names.append(act.activity_name)

        aligned_sum = sum(
            getattr(a, attr)
            for a in activities
            if a.is_eligible and a.is_aligned and a.dnsh_compliant and a.min_safeguards_compliant
        )
        return {
            "total_eur": round(total, 2),
            "aligned_eur": round(aligned_sum, 2),
            "aligned_pct": round((aligned_sum / total) * 100.0, 2),
            "non_material_excluded_pct": round((excluded_sum / total) * 100.0, 2),
            "non_material_excluded": excluded_names,
        }

    return {
        "turnover": compute_ratio("turnover_eur"),
        "capex": compute_ratio("capex_eur"),
        "opex": compute_ratio("opex_eur"),
    }


# =====================================================================
# MOTOR 4: SOSTENIBILIDAD TIC (EED 2024/1364) Y SCI (ISO/IEC 21031)
# =====================================================================
def calculate_ict_sustainability(
    installed_it_power_kw: float,
    nominal_energy_input_mw: float,
    e_dc_kwh: float,
    e_it_kwh: float,
    w_in_m3: float,
    e_reuse_kwh: float,
    e_res_tot_kwh: float,
    sw_energy_kwh: float,
    grid_intensity_gco2_kwh: float,
    embodied_hardware_gco2: float,
    functional_units: float,
) -> Dict[str, Any]:
    pue = round(e_dc_kwh / e_it_kwh, 3)
    e_it_mwh = e_it_kwh / 1000.0  # Conversión obligatoria kWh -> MWh para WUE (m3/MWh)
    wue = round(w_in_m3 / e_it_mwh, 3) if e_it_mwh > 0 else 0.0
    erf = round(e_reuse_kwh / e_dc_kwh, 3)
    ref = round(e_res_tot_kwh / e_dc_kwh, 3)
    sci = round(((sw_energy_kwh * grid_intensity_gco2_kwh) + embodied_hardware_gco2) / functional_units, 4)

    return {
        "pue": pue,
        "wue": wue,
        "erf": erf,
        "ref": ref,
        "eed_reporting_obligated": installed_it_power_kw >= config.EED_DATACENTER_THRESHOLD_KW,
        "waste_heat_alert": nominal_energy_input_mw > config.EED_WASTE_HEAT_THRESHOLD_MW,
        "eu_avg_pue_benchmark": 1.36,
        "sci_gco2_per_unit": sci,
    }


# =====================================================================
# MOTOR 5: ECONOMÍA CIRCULAR (ESRS E5) Y GS1 DIGITAL LINK (DPP)
# =====================================================================
def build_dpp_metrics(gtin: str, serial: str, total_mass_kg: float, recycled_content_kg: float) -> Dict[str, Any]:
    recycled_pct = round((min(recycled_content_kg, total_mass_kg) / total_mass_kg) * 100.0, 2)
    gs1_uri = f"https://id.gs1.org/01/{gtin}/21/{serial}"
    return {"recycled_content_pct": recycled_pct, "gs1_digital_link": gs1_uri}


# =====================================================================
# MOTOR 6: MADUREZ DIGITAL EDIH (DMA) Y ALERTAS CRA 24H
# =====================================================================
def calculate_dma_score(d1: float, d2: float, d3: float, d4: float, d5: float, d6: float) -> Tuple[float, str]:
    avg = round((d1 + d2 + d3 + d4 + d5 + d6) / 6.0, 2)
    if avg <= 25.0:
        level = "Básico (0-25%)"
    elif avg <= 50.0:
        level = "Medio (26-50%)"
    elif avg <= 75.0:
        level = "Moderadamente Avanzado (51-75%)"
    else:
        level = "Avanzado (76-100%)"
    return avg, level


def calculate_cra_24h_deadline() -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=24)