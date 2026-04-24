import uvicorn

from .config import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run("unoq_backend.app:app", host=settings.bind, port=settings.port, reload=False)


if __name__ == "__main__":
    main()

