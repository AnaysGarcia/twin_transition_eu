# TwinTransition EU Platform (2026–2029)

Plataforma modular en Python orientada al cumplimiento normativo de la **Transformación Gemela (*Twin Transition*) de la Unión Europea**, integrando descarbonización, economía circular, eficiencia TIC y soberanía digital en una arquitectura auditable y preparada para proyectos subvencionables (FEDER/CDTI, Horizonte Europa, DIGITAL Europe).

## Módulos y Motores Normativos Implementados

1. **Huella de Carbono Corporativa (GHG Protocol, ESRS E1 y RD 214/2025):** Cálculo simultáneo *location-based* y *market-based* con series versionadas de factores MITECO (2024–2026), bloqueo anti-doble conteo de Garantías de Origen (GdO) y clasificación automática de obligaciones (CSRD Ómnibus / VSME / EINF).
2. **CBAM Fase Definitiva (Reg. (UE) 2023/956 y 2025/2083):** Control del umbral anual de 50 toneladas netas, recargos escalonados por valores por defecto (+10%/+20%/+30% general y +1% fertilizantes), precios trimestrales RCDE UE 2026, códigos aduaneros TARIC (`Y128` / `Y137`) y regla de tenencia del 50%.
3. **Taxonomía UE (Reg. Delegado (UE) 2026/73):** Cálculo de KPIs de Facturación, CapEx y OpEx con filtro automático de materialidad del 10%.
4. **Sostenibilidad TIC y Software Verde:** Indicadores de centros de datos según Directiva EED / Reg. Delegado (UE) 2024/1364 (`PUE`, `WUE`, `ERF`, `REF` y alerta de calor residual >1 MW) e intensidad de carbono del software (`SCI`, ISO/IEC 21031:2024).
5. **Pasaporte Digital de Producto (ESPR / EN 18216–18223):** Generación de identificadores **GS1 Digital Link**, métricas de circularidad (ESRS E5) y huella PEF EF 3.1.
6. **Madurez Digital EDIH (DMA), DNSH, RGPD y CRA:** Evaluación longitudinal DMA (T0/T1/T2), autoevaluación de los 6 objetivos **DNSH**, registro anonimizado de consentimientos RGPD (SHA-256), alertas de vulnerabilidades **CRA 24h** (ENISA) y cadena de auditoría criptográfica inmutable (SHA-256).

## Reportes Legibles por Máquina

* **VSME / XBRL-Ready (JSON):** `/api/export/{company_id}/vsme`
* **Declaración CBAM (JSON):** `/api/export/{company_id}/cbam`
* **Pasaporte Digital de Producto (JSON-LD):** `/api/export/dpp/{dpp_id}/jsonld`
* **SBOM CycloneDX 1.5 (CRA):** `/api/export/sbom/cyclonedx`
* **EDIH DMA (CSV):** `/api/export/{company_id}/dma/csv`
* **Portabilidad total Data Act / RGPD (JSON):** `/api/export/{company_id}/portability`
* **Verificación de cadena de auditoría SHA-256:** `/api/audit-trail`

## Estructura del Proyecto

```text
twin_transition_eu/
├── config.py           # Constantes normativas UE 2026 (MITECO, CBAM, umbrales)
├── db.py               # Configuración SQLAlchemy (SQLite portable a PostgreSQL)
├── models.py           # Esquema ORM de entidades y cadena de auditoría
├── schemas.py          # Validación estricta de datos con Pydantic v2
├── engines.py          # 6 motores de cálculo normativo + sellado SHA-256
├── exporters.py        # Exportadores JSON-LD, CycloneDX, VSME, CBAM, CSV y Data Act
├── seed_data.py        # Precarga de factores MITECO y pyme industrial demo
├── templates/
│   └── dashboard.html  # Cuadro de mando web y simuladores interactivos
├── app.py              # Aplicación FastAPI (API REST y vistas)
├── main.py             # Punto de entrada del servidor Uvicorn
└── requirements.txt    # Dependencias del proyecto
```

## Requisitos e Instalación Local

Requiere **Python 3.10 o superior** (FastAPI, Uvicorn, SQLAlchemy, Pydantic v2 y Jinja2).

```bash
# 1. Clonar el repositorio
git clone [https://github.com/AnaysGarcia/twin_transition_eu.git](https://github.com/AnaysGarcia/twin_transition_eu.git)
cd twin_transition_eu

# 2. Crear y activar entorno virtual
python -m venv venv
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Linux / macOS:
source venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Ejecutar la plataforma
python main.py
```

## Acceso a la Aplicación

Una vez iniciado `main.py`, el programa crea automáticamente la base de datos local con datos de demostración y expone:

* **Cuadro de Mando Web:** `http://127.0.0.1:8000`
* **Documentación interactiva API (Swagger / OpenAPI):** `http://127.0.0.1:8000/docs`
  
