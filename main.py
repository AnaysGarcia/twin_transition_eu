import uvicorn
from db import SessionLocal, init_db
from seed_data import seed_initial_data


def bootstrap():
    """Inicializa la base de datos y precarga factores MITECO/CBAM y la empresa demo."""
    init_db()
    db = SessionLocal()
    try:
        seed_initial_data(db)
    finally:
        db.close()


if __name__ == "__main__":
    bootstrap()
    print("Servidor TwinTransition EU 2026 iniciado en: http://127.0.0.1:8000")
    print("Documentación interactiva API (Swagger):    http://127.0.0.1:8000/docs")
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)