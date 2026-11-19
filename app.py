import hashlib
from pathlib import Path
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

import config
import engines
import exporters
import models
import schemas
from db import get_db

app = FastAPI(
    title=config.APP_NAME,
    version=config.APP_VERSION,
    description="Software modular de Transformación Gemela UE (CSRD/VSME, CBAM, Taxonomía 2026/73, EED/SCI, DPP, DMA, DNSH, CRA y Data Act).",
)

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _get_company_or_404(db: Session, company_id: int) -> models.Company:
    company = db.query(models.Company).filter_by(id=company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return company


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    company = db.query(models.Company).first()
    if not company:
        return HTMLResponse("<h1>Sin datos iniciales. Ejecuta main.py para inicializar.</h1>")

    s12_loc = round(sum(e.tco2e_location_based for e in company.emissions if e.scope in (1, 2)), 2)
    s12_mkt = round(sum(e.tco2e_market_based for e in company.emissions if e.scope in (1, 2)), 2)
    cbam_cost = round(sum(c.estimated_cost_eur for c in company.cbam_imports), 2)
    cbam_certs = round(sum(c.certificates_required for c in company.cbam_imports), 3)
    cbam_mass = round(sum(c.net_mass_tonnes for c in company.cbam_imports), 2)
    taxonomy = engines.calculate_taxonomy_kpis(company.taxonomy_activities)
    last_ict = company.ict_metrics[-1] if company.ict_metrics else None
    last_dma = company.dma_assessments[-1] if company.dma_assessments else None
    dnsh_ok = all(d.overall_compliant for d in company.dnsh_assessments) if company.dnsh_assessments else False

    summary = {
        "obligations": engines.classify_company_obligations(company),
        "carbon": {"scope1_2_location_tco2e": s12_loc, "scope1_2_market_tco2e": s12_mkt},
        "cbam": {
            "total_cost_eur": cbam_cost,
            "total_certs": cbam_certs,
            "total_mass_t": cbam_mass,
            "holding_50pct": round(cbam_certs * 0.5, 3),
        },
        "taxonomy": taxonomy,
        "ict": {
            "pue": last_ict.pue if last_ict else 0,
            "wue": last_ict.wue if last_ict else 0,
            "sci": last_ict.sci_gco2_per_unit if last_ict else 0,
            "waste_heat_alert": last_ict.waste_heat_alert if last_ict else False,
        },
        "dma": {
            "stage": last_dma.stage if last_dma else "N/A",
            "overall_score": last_dma.overall_score if last_dma else 0,
            "level": last_dma.maturity_level if last_dma else "Sin evaluar",
        },
        "dnsh_ok": dnsh_ok,
        "first_dpp_id": company.dpps[0].id if company.dpps else None,
    }
    return templates.TemplateResponse(request, "dashboard.html", {"company": company, "summary": summary})


# -------------------- MOTORES DE CÁLCULO (POST) --------------------

@app.post("/api/carbon")
def add_carbon_record(payload: schemas.EmissionCreate , db: Session = Depends(get_db)):
    _get_company_or_404(db, payload.company_id)
    loc, mkt, vtag, warning = engines.calculate_carbon_emission(
        db, payload.reporting_year, payload.scope, payload.activity_key,
        payload.activity_amount, payload.has_gdo_certificate, payload.evidence_ref,
    )
    record = models.EmissionRecord(
        **payload.model_dump(),
        factor_version=vtag,
        tco2e_location_based=loc,
        tco2e_market_based=mkt,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    audit = engines.record_audit(db , "CARBON_RD214" , "CALCULATE" , {"id": record.id, "loc": loc, "mkt": mkt})
    return {
        "id": record.id,
        "tco2e_location_based": loc,
        "tco2e_market_based": mkt,
        "factor_version": vtag,
        "warning": warning,
        "audit_hash": audit.record_hash,
    }


@app.post("/api/cbam")
def add_cbam_import(payload: schemas.CBAMImportCreate , db: Session = Depends(get_db)):
    _get_company_or_404(db, payload.company_id)
    res = engines.calculate_cbam_liability(
        db, payload.company_id, payload.reporting_year, payload.quarter,
        payload.cn_code, payload.sector, payload.net_mass_tonnes,
        payload.is_verified_actual, payload.see_input_tco2e_t, payload.art9_deduction_certs,
    )
    record = models.CBAMImport(
        company_id=payload.company_id,
        reporting_year=payload.reporting_year,
        quarter=payload.quarter,
        cn_code=payload.cn_code,
        sector=payload.sector,
        origin_country=payload.origin_country,
        net_mass_tonnes=payload.net_mass_tonnes,
        is_verified_actual=payload.is_verified_actual,
        see_input_tco2e_t=payload.see_input_tco2e_t or res["effective_see"],
        effective_see_tco2e_t=res["effective_see"],
        benchmark_tco2e_t=res["benchmark"],
        free_allocation_factor=res["free_allocation_factor"],
        art9_deduction_certs=payload.art9_deduction_certs,
        ets_price_eur=res["ets_price_eur"],
        certificates_required=res["certificates_required"],
        estimated_cost_eur=res["estimated_cost_eur"],
        taric_code=res["taric_code"],
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    audit = engines.record_audit(db , "CBAM_2026" , "CALCULATE" , {"id": record.id, **res})
    return {"id": record.id, **res, "audit_hash": audit.record_hash}


@app.post("/api/taxonomy")
def add_taxonomy_activity(payload: schemas.TaxonomyActivityCreate , db: Session = Depends(get_db)):
    company = _get_company_or_404(db, payload.company_id)
    act = models.TaxonomyActivity(**payload.model_dump())
    db.add(act)
    db.commit()
    db.refresh(company)
    kpis = engines.calculate_taxonomy_kpis(company.taxonomy_activities)
    engines.record_audit(db , "TAXONOMY_2026_73" , "RECALCULATE" , kpis)
    return kpis


@app.post("/api/ict-sustainability")
def add_ict_sustainability(payload: schemas.ICTSustainabilityCreate , db: Session = Depends(get_db)):
    _get_company_or_404(db, payload.company_id)
    res = engines.calculate_ict_sustainability(
        payload.installed_it_power_kw, payload.nominal_energy_input_mw,
        payload.e_dc_kwh, payload.e_it_kwh, payload.w_in_m3,
        payload.e_reuse_kwh, payload.e_res_tot_kwh,
        payload.sw_energy_kwh, payload.grid_intensity_gco2_kwh,
        payload.embodied_hardware_gco2, payload.functional_units,
    )
    rec = models.ICTSustainabilityRecord(
        **payload.model_dump(),
        pue=res["pue"], wue=res["wue"], erf=res["erf"], ref=res["ref"],
        waste_heat_alert=res["waste_heat_alert"], sci_gco2_per_unit=res["sci_gco2_per_unit"],
    )
    db.add(rec)
    db.commit()
    engines.record_audit(db , "EED_SCI" , "CALCULATE" , res)
    return res


@app.post("/api/dpp")
def create_dpp(payload: schemas.DPPCreate , db: Session = Depends(get_db)):
    company = _get_company_or_404(db, payload.company_id)
    metrics = engines.build_dpp_metrics(
        payload.gtin, payload.serial_number, payload.total_mass_kg, payload.recycled_content_kg
    )
    dpp = models.DigitalProductPassport(**payload.model_dump() , gs1_digital_link=metrics["gs1_digital_link"])
    db.add(dpp)
    db.commit()
    db.refresh(dpp)
    engines.record_audit(db , "DPP_ESPR" , "CREATE" , {"dpp_id": dpp.id, "uri": dpp.gs1_digital_link})
    return exporters.export_dpp_jsonld(dpp , company)


@app.post("/api/dma")
def create_dma(payload: schemas.DMACreate , db: Session = Depends(get_db)):
    _get_company_or_404(db, payload.company_id)
    avg, level = engines.calculate_dma_score(
        payload.d1_strategy, payload.d2_readiness, payload.d3_human_centric,
        payload.d4_data_security, payload.d5_automation_ai, payload.d6_green_digital,
    )
    rec = models.DMAAssessment(**payload.model_dump() , overall_score=avg , maturity_level=level)
    db.add(rec)
    db.commit()
    engines.record_audit(db , "EDIH_DMA" , "ASSESS" , {"stage": payload.stage, "score": avg, "level": level})
    return {"overall_score": avg, "maturity_level": level, "stage": payload.stage}


@app.post("/api/dnsh")
def create_dnsh(payload: schemas.DNSHCreate , db: Session = Depends(get_db)):
    _get_company_or_404(db, payload.company_id)
    compliant = all([
        payload.obj1_mitigation_ok, payload.obj2_adaptation_ok, payload.obj3_water_ok,
        payload.obj4_circular_ok, payload.obj5_pollution_ok, payload.obj6_biodiversity_ok,
    ])
    rec = models.DNSHAssessment(**payload.model_dump() , overall_compliant=compliant)
    db.add(rec)
    db.commit()
    engines.record_audit(db , "DNSH_SUBVENCIONES" , "EVALUATE" , {"project": payload.project_name, "compliant": compliant})
    return {"project_name": payload.project_name, "overall_compliant": compliant}


@app.post("/api/gdpr/consent")
def record_gdpr_consent(payload: schemas.GDPRConsentCreate , db: Session = Depends(get_db)):
    subject_hash = hashlib.sha256(payload.subject_identifier.encode("utf-8")).hexdigest()
    rec = models.GDPRConsent(subject_hash=subject_hash , purpose=payload.purpose , granted=payload.granted)
    db.add(rec)
    db.commit()
    return {"status": "CONSENT_RECORDED", "subject_hash": subject_hash}


@app.post("/api/cra/incident")
def log_cra_incident(payload: schemas.CRAIncidentCreate , db: Session = Depends(get_db)):
    deadline = engines.calculate_cra_24h_deadline()
    rec = models.CRAVulnerabilityIncident(
        cve_id=payload.cve_id,
        component_name=payload.component_name,
        actively_exploited=payload.actively_exploited,
        enisa_deadline_24h=deadline,
    )
    db.add(rec)
    db.commit()
    engines.record_audit(db , "CRA_ART14" , "ALERT_24H" , {"cve": payload.cve_id, "deadline": deadline.isoformat()})
    return {"cve_id": rec.cve_id, "enisa_24h_deadline_utc": deadline.isoformat(), "status": rec.status}


# -------------------- EXPORTADORES LEGIBLES POR MÁQUINA (GET) --------------------

@app.get("/api/export/{company_id}/vsme")
def get_vsme_export(company_id: int, db: Session = Depends(get_db)):
    company = _get_company_or_404(db, company_id)
    return exporters.export_vsme_report(db , company)


@app.get("/api/export/{company_id}/cbam")
def get_cbam_export(company_id: int, db: Session = Depends(get_db)):
    company = _get_company_or_404(db, company_id)
    return exporters.export_cbam_declaration(company)


@app.get("/api/export/dpp/{dpp_id}/jsonld")
def get_dpp_jsonld(dpp_id: int, db: Session = Depends(get_db)):
    dpp = db.query(models.DigitalProductPassport).filter_by(id=dpp_id).first()
    if not dpp:
        raise HTTPException(status_code=404, detail="DPP no encontrado")
    return exporters.export_dpp_jsonld(dpp , dpp.company)


@app.get("/api/export/sbom/cyclonedx")
def get_sbom():
    return exporters.export_sbom_cyclonedx()


@app.get("/api/export/{company_id}/dma/csv", response_class=PlainTextResponse)
def get_dma_csv(company_id: int, db: Session = Depends(get_db)):
    company = _get_company_or_404(db, company_id)
    return exporters.export_dma_csv(company)


@app.get("/api/export/{company_id}/portability")
def get_portability(company_id: int, db: Session = Depends(get_db)):
    company = _get_company_or_404(db, company_id)
    return exporters.export_data_act_portability(db , company)


@app.get("/api/audit-trail")
def get_audit_status(db: Session = Depends(get_db)):
    return engines.verify_audit_chain(db)