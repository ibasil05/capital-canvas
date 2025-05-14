"""
Exports package for CapitalCanvas.
Handles exporting models to Excel and PowerPoint files.
"""

from exports.excel import ExcelExport
from exports.powerpoint import PowerPointExport
from exports.excel_export import generate_excel_export
from exports.ppt_export import generate_ppt_export

__all__ = ['ExcelExport', 'PowerPointExport']

# This file can be empty or used to mark the directory as a Python package. 

async def export_model(model_id: str, format: str, user_id: str | None = None):
    """Helper used by API to generate export and return S3/public URL or raw bytes.
    For now simply generates the file and uploads via db.upload_export_file (to keep logic centralised).
    """
    from db import db  # lazy import to avoid circular
    # Fetch model data (service role)
    model_row = await db.get_model_by_id(model_id)
    if not model_row:
        raise ValueError("Model not found")
    # Parse results JSON
    import json, io
    results_json = model_row.get("results_json")
    if isinstance(results_json, str):
        results_json = json.loads(results_json)
    # Generate file bytes
    if format == "xlsx":
        file_bytes = await generate_excel_export(results_json)
        ext = "xlsx"
    elif format == "pptx":
        file_bytes = await generate_ppt_export(results_json)
        ext = "pptx"
    else:
        raise ValueError("Unsupported format")
    # Upload to storage
    import time
    file_name = f"{model_row.get('ticker','model')}_{int(time.time())}.{ext}"
    file_url = await db.upload_export_file(user_id or model_row.get("user_id"), file_name, file_bytes)
    return file_url 