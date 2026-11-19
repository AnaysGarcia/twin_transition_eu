from sqlalchemy.orm import Session
import config
import engines
import models


def seed_initial_data(db: Session):
    # 1. Precargar series de factores MITECO 2024, 2025 y 2026
    if db.query(models.EmissionFactorVersion).count() == 0:
        for year, factors in config.MITECO_FACTORS.items():
            for key, val in factors.items():
                db.add(
                    models.EmissionFactorVersion(
                        year=year,
                        activity_key=key,
                        factor_kg_co2e=val,
                        source="MITECO / OECC Oficial",
                        version_tag="v2026.05",
                    )
                )
        db.commit()

    # 2. Precargar empresa industrial demo si la BD está vacía
    if db.query(models.Company).count() > 0:
        return

    company = models.Company(
        name="Aceros y Componentes del Cantábrico S.L.",
        nif="B33987654",
        country_code="ES",
        sector_cnae="2410 - Fabricación de productos básicos de hierro y acero",
        employees=185,
        turnover_eur=32_500_000.0,
        total_assets_eur=18_200_000.0,
        is_public_interest_entity=False,
    )
    db.add(company)
    db.commit()
    db.refresh(company)

    # 3. Registros de Huella de Carbono (RD 214/2025 y VSME)
    sample_emissions = [
        (2025, "ES", 1, "gas_natural_kwh", 450_000.0, "kWh", False, "FACT-GN-2025"),
        (2025, "ES", 1, "gasoleo_diesel_litro", 28_000.0, "litros", False, "FACT-FLOTA-2025"),
        (2025, "ES", 2, "electricidad_mix_es_kwh", 1_200_000.0, "kWh", True, "GDO-CNMC-2025-001"),
        (2025, "ES", 2, "electricidad_mix_es_kwh", 350_000.0, "kWh", False, "FACT-ELEC-NAV2"),
    ]
    for yr, cc, sc, key, amt, unit, gdo, ref in sample_emissions:
        loc, mkt, vtag, _ = engines.calculate_carbon_emission(db , yr , sc , key , amt , gdo , ref)
        db.add(
            models.EmissionRecord(
                company_id=company.id,
                reporting_year=yr,
                country_code=cc,
                scope=sc,
                activity_key=key,
                activity_amount=amt,
                unit=unit,
                has_gdo_certificate=gdo,
                evidence_ref=ref,
                factor_version=vtag,
                tco2e_location_based=loc,
                tco2e_market_based=mkt,
            )
        )

    # 4. Importaciones CBAM 2026 (ejemplo real del informe: clínker Turquía + acero)
    cbam_res = engines.calculate_cbam_liability(
        db, company.id, 2026, "2026-Q3", "2523 10 00", "cemento", 120.0, False, 1.410, 0.0
    )
    db.add(
        models.CBAMImport(
            company_id=company.id,
            reporting_year=2026,
            quarter="2026-Q3",
            cn_code="2523 10 00",
            sector="cemento",
            origin_country="Turquía",
            net_mass_tonnes=120.0,
            is_verified_actual=False,
            see_input_tco2e_t=1.410,
            effective_see_tco2e_t=cbam_res["effective_see"],
            benchmark_tco2e_t=cbam_res["benchmark"],
            free_allocation_factor=cbam_res["free_allocation_factor"],
            ets_price_eur=cbam_res["ets_price_eur"],
            certificates_required=cbam_res["certificates_required"],
            estimated_cost_eur=cbam_res["estimated_cost_eur"],
            taric_code=cbam_res["taric_code"],
        )
    )

    # 5. Actividades de Taxonomía UE (demostración filtro 10% Reg. Del. 2026/73)
    db.add_all([
        models.TaxonomyActivity(
            company_id=company.id, reporting_year=2026, activity_name="Acero eléctrico bajo en carbono",
            turnover_eur=24_000_000.0, capex_eur=1_800_000.0, opex_eur=650_000.0,
            is_eligible=True, is_aligned=True, dnsh_compliant=True, min_safeguards_compliant=True
        ),
        models.TaxonomyActivity(
            company_id=company.id, reporting_year=2026, activity_name="Mecanizado auxiliar no alineado",
            turnover_eur=1_500_000.0, capex_eur=120_000.0, opex_eur=50_000.0,
            is_eligible=False, is_aligned=False, dnsh_compliant=False, min_safeguards_compliant=True
        ),
        models.TaxonomyActivity(
            company_id=company.id, reporting_year=2026, activity_name="Servicios de logística secundaria",
            turnover_eur=7_000_000.0, capex_eur=400_000.0, opex_eur=220_000.0,
            is_eligible=True, is_aligned=False, dnsh_compliant=True, min_safeguards_compliant=True
        ),
    ])

    # 6. Registro Sostenibilidad TIC (EED 2024/1364 + SCI ISO/IEC 21031)
    ict_res = engines.calculate_ict_sustainability(
        installed_it_power_kw=620.0, nominal_energy_input_mw=1.15,
        e_dc_kwh=4_800_000.0, e_it_kwh=3_600_000.0, w_in_m3=2_100.0,
        e_reuse_kwh=720_000.0, e_res_tot_kwh=4_080_000.0,
        sw_energy_kwh=120.0, grid_intensity_gco2_kwh=258.0,
        embodied_hardware_gco2=4500.0, functional_units=100_000.0,
    )
    db.add(
        models.ICTSustainabilityRecord(
            company_id=company.id, facility_name="CPD Industrial Gijón Norte",
            installed_it_power_kw=620.0, nominal_energy_input_mw=1.15,
            e_dc_kwh=4_800_000.0, e_it_kwh=3_600_000.0, w_in_m3=2_100.0,
            e_reuse_kwh=720_000.0, e_res_tot_kwh=4_080_000.0,
            pue=ict_res["pue"], wue=ict_res["wue"], erf=ict_res["erf"], ref=ict_res["ref"],
            waste_heat_alert=ict_res["waste_heat_alert"],
            sw_energy_kwh=120.0, grid_intensity_gco2_kwh=258.0,
            embodied_hardware_gco2=4500.0, functional_units=100_000.0,
            sci_gco2_per_unit=ict_res["sci_gco2_per_unit"],
        )
    )

    # 7. Pasaporte Digital de Producto (DPP - EN 18216-18223)
    dpp_m = engines.build_dpp_metrics("08412345678905" , "ACERO-2026-0001" , 1000.0 , 780.0)
    db.add(
        models.DigitalProductPassport(
            company_id=company.id, gtin="08412345678905", serial_number="ACERO-2026-0001",
            product_name="Bobina Acero Estructural Eco-EAF", category="acero",
            pef_carbon_footprint_kgco2e=640.0, total_mass_kg=1000.0,
            recycled_content_kg=780.0, waste_diverted_pct=94.5,
            repairability_score=8.7, gs1_digital_link=dpp_m["gs1_digital_link"],
        )
    )

    # 8. Evaluación de Madurez Digital EDIH (DMA T0)
    avg, level = engines.calculate_dma_score(68 , 72 , 60 , 78 , 55 , 80)
    db.add(
        models.DMAAssessment(
            company_id=company.id, stage="T0",
            d1_strategy=68, d2_readiness=72, d3_human_centric=60,
            d4_data_security=78, d5_automation_ai=55, d6_green_digital=80,
            overall_score=avg, maturity_level=level,
        )
    )

    # 9. Autoevaluación DNSH para solicitud de subvención (CDTI / FEDER / Horizonte)
    db.add(
        models.DNSHAssessment(
            company_id=company.id,
            project_name="Plataforma Gemelo Verde-Digital con Conector EDC",
            intervention_field_code="021ter",
            climate_tag_pct=40,
            digital_tag_pct=100,
            overall_compliant=True,
            evidence_notes="CPD con PUE 1.33 y 85% energía renovable; SCI monitorizado ISO/IEC 21031.",
        )
    )

    db.commit()
    engines.record_audit(db , "SYSTEM" , "SEED_INITIAL_DATA" , {"company_id": company.id, "status": "READY"})