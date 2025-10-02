import os
from pathlib import Path
from urllib.parse import quote_plus


def auto_load(strict=False) -> list[str]:
    parent = Path(__file__).parent
    print(parent)
    if parent.joinpath("models.py").exists():
        return ["models"]
    models_dir = Path(parent, "models")
    if not models_dir.exists():
        raise RuntimeError("models.py and models/ not found!")
    files = [p for p in models_dir.glob("*.py") if p.name[0] != "_"]
    if strict:
        files = [p for p in files if b"tortoise" in p.read_bytes()]
    return [f"models.{p.stem}" for p in files]


DB_NAME = "ewbeqxaepnaurvoozukt"
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = quote_plus(os.getenv("POSTGRES_PASSWORD", "postgres"))
DB_URL = f"postgres://{DB_USER}:{DB_PASSWORD}@9qasp5v56q8ckkf5dc.apn.leapcellpool.com:6438/{DB_NAME}"
TORTOISE_ORM = {
    "connections": {"default": DB_URL},
    "apps": {"models": {"models": [*auto_load(), "aerich.models"]}},
}
