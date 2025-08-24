"""Application entry point."""

import uvicorn

from src.app.main import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, access_log=False)  # noqa: S104
