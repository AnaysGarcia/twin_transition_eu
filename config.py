import os

APP_NAME = "TwinTransition EU Platform"
APP_VERSION = "1.0.0-eu2026"

# Base de datos SQLite por defecto (portable a PostgreSQL vía variable de entorno - Data Act Cap. VI)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./twin_transition_eu.db")

# Umbrales normativos vigentes (noviembre 2026)
CSRD_MIN_EMPLOYEES = 1000
CSRD_MIN_TURNOVER_EUR = 450_000_000.0
CBAM_MASS_THRESHOLD_TONNES = 50.0
EED_DATACENTER_THRESHOLD_KW = 500.0
EED_WASTE_HEAT_THRESHOLD_MW = 1.0
TAXONOMY_MATERIALITY_LIMIT_PCT = 10.0

# Series oficiales MITECO (kgCO2e por unidad de actividad)
MITECO_FACTORS = {
    2024: {
        "electricidad_mix_es_kwh": 0.283,
        "electricidad_gdo_kwh": 0.0,
        "gas_natural_kwh": 0.202,
        "gasoleo_diesel_litro": 2.69,
        "vehiculo_diesel_km": 0.168,
    },
    2025: {
        "electricidad_mix_es_kwh": 0.258,  # Descenso del 8,83% respecto a 2024
        "electricidad_gdo_kwh": 0.0,
        "gas_natural_kwh": 0.202,
        "gasoleo_diesel_litro": 2.69,
        "vehiculo_diesel_km": 0.168,
    },
    2026: {
        "electricidad_mix_es_kwh": 0.258,  # Última serie publicada disponible hasta cierre 2026
        "electricidad_gdo_kwh": 0.0,
        "gas_natural_kwh": 0.202,
        "gasoleo_diesel_litro": 2.69,
        "vehiculo_diesel_km": 0.168,
    },
}

# Precios trimestrales RCDE UE para certificados CBAM 2026 (€/tCO2e)
CBAM_ETS_QUARTERLY_PRICES_2026 = {
    "2026-Q1": 75.36,
    "2026-Q2": 75.28,
    "2026-Q3": 82.32,
    "2026-Q4": 82.32,  # Estimación provisional hasta publicación oficial
}

# Factor de asignación gratuita RCDE UE (cae 2,5% anual en 2026-2027 hasta extinguirse en 2034)
CBAM_FREE_ALLOCATION_FACTOR = {
    2026: 0.975,
    2027: 0.950,
    2028: 0.900,
    2029: 0.775,
    2030: 0.515,
    2031: 0.390,
    2032: 0.265,
    2033: 0.140,
    2034: 0.000,
}

# Recargos por uso de valores por defecto en CBAM fase definitiva
CBAM_DEFAULT_MARKUP = {
    "general": {2026: 0.10, 2027: 0.20, 2028: 0.30},
    "fertilizantes": {2026: 0.01, 2027: 0.01, 2028: 0.01},
}

# Benchmarks CBAM de referencia (tCO2e/t) por código NC/TARIC
CBAM_BENCHMARKS = {
    "2523 10 00": {"descripcion": "Clínker gris de cemento", "sector": "cemento", "benchmark": 0.666, "default_see": 1.410},
    "7207 11 14": {"descripcion": "Semiproductos de hierro o acero", "sector": "hierro_acero", "benchmark": 1.328, "default_see": 2.210},
    "7601 10 00": {"descripcion": "Aluminio sin alear", "sector": "aluminio", "benchmark": 1.464, "default_see": 8.600},
    "3102 10 19": {"descripcion": "Urea (fertilizante)", "sector": "fertilizantes", "benchmark": 0.902, "default_see": 1.390},
}