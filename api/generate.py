import os
import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from src.mpm_summary.pipeline import run_pipeline

app = FastAPI()


@app.get("/api/health")
def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})


@app.get("/api/generate")
def generate_pdf() -> FileResponse:
    try:
        temp_dir = Path(tempfile.gettempdir())
        os.environ["OUTPUT_DIR"] = str(temp_dir)
        generated_paths = run_pipeline()
        output_path = Path(generated_paths[0])
        return FileResponse(
            path=str(output_path),
            media_type="application/pdf",
            filename=output_path.name,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
