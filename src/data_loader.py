"""
Data Ingestion Module.
Robust data loader for CSV and Excel files with encoding detection,
delimiter auto-detection, sheet selection, and metadata profiling.
"""
import io
import os
from typing import Tuple, Dict, Any, Optional, List, Union
import pandas as pd
from src.logger import log_event


def get_excel_sheet_names(file_source: Union[str, io.BytesIO, bytes]) -> List[str]:
    """Retrieve list of sheet names from an Excel file without loading entire data."""
    try:
        excel_file = pd.ExcelFile(file_source)
        return excel_file.sheet_names
    except Exception as e:
        log_event("WARNING", "LOAD", f"Could not extract sheet names: {str(e)}")
        return []


def load_data(
    file_source: Union[str, io.BytesIO, bytes],
    file_name: Optional[str] = None,
    sheet_name: Optional[Union[str, int]] = 0,
    delimiter: Optional[str] = None,
    encoding: Optional[str] = None
) -> Tuple[Optional[pd.DataFrame], Dict[str, Any]]:
    """
    Load CSV or Excel dataset with robust fallbacks and extract rich metadata.
    
    Args:
        file_source: File path, BytesIO buffer, or raw bytes
        file_name: Name of file (optional, used for format inference)
        sheet_name: Sheet name or index for Excel files
        delimiter: Explicit delimiter (optional; auto-detected if None)
        encoding: Explicit encoding (optional; auto-detected if None)
        
    Returns:
        Tuple of (DataFrame or None, metadata_dict)
    """
    metadata: Dict[str, Any] = {
        "file_name": file_name or (os.path.basename(file_source) if isinstance(file_source, str) else "uploaded_file"),
        "file_type": "unknown",
        "file_size_kb": 0.0,
        "rows": 0,
        "columns": 0,
        "column_names": [],
        "memory_kb": 0.0,
        "initial_missing_count": 0,
        "initial_duplicate_count": 0,
        "available_sheets": [],
        "selected_sheet": sheet_name,
        "success": False,
        "error_message": None
    }

    try:
        # Determine file size
        if isinstance(file_source, str) and os.path.exists(file_source):
            metadata["file_size_kb"] = round(os.path.getsize(file_source) / 1024, 2)
            fname = file_source.lower()
        elif hasattr(file_source, "size"): # Streamlit UploadedFile
            metadata["file_size_kb"] = round(file_source.size / 1024, 2)
            fname = (file_name or getattr(file_source, "name", "")).lower()
        elif isinstance(file_source, io.BytesIO):
            metadata["file_size_kb"] = round(len(file_source.getvalue()) / 1024, 2)
            fname = (file_name or "").lower()
        else:
            fname = (file_name or "").lower()

        # Determine file format
        is_excel = fname.endswith(".xlsx") or fname.endswith(".xls") or fname.endswith(".xlsm")
        is_csv = fname.endswith(".csv") or fname.endswith(".txt") or fname.endswith(".tsv")

        df = None

        if is_excel:
            metadata["file_type"] = "Excel"
            # Extract available sheet names
            sheets = get_excel_sheet_names(file_source)
            metadata["available_sheets"] = sheets
            
            # Reset pointer if BytesIO
            if hasattr(file_source, "seek"):
                file_source.seek(0)
                
            actual_sheet = sheet_name if sheet_name in sheets or isinstance(sheet_name, int) else 0
            df = pd.read_excel(file_source, sheet_name=actual_sheet)
            metadata["selected_sheet"] = actual_sheet

        else:
            # CSV / Plain text handling with encoding fallbacks
            metadata["file_type"] = "CSV"
            encodings_to_try = [encoding] if encoding else ["utf-8", "utf-8-sig", "latin1", "cp1252", "iso-8859-1"]
            
            last_err = None
            for enc in encodings_to_try:
                if not enc:
                    continue
                try:
                    if hasattr(file_source, "seek"):
                        file_source.seek(0)
                    
                    # Try sep=None (python engine auto-sniffer) if delimiter is not specified
                    if delimiter:
                        df = pd.read_csv(file_source, sep=delimiter, encoding=enc)
                    else:
                        try:
                            df = pd.read_csv(file_source, sep=None, engine="python", encoding=enc)
                        except Exception:
                            if hasattr(file_source, "seek"):
                                file_source.seek(0)
                            df = pd.read_csv(file_source, sep=",", encoding=enc)
                    break
                except Exception as ex:
                    last_err = ex
                    continue
            
            if df is None:
                raise ValueError(f"Failed to read CSV with supported encodings: {last_err}")

        # Check for empty dataset
        if df is None or df.empty:
            if df is not None and len(df.columns) > 0:
                metadata["columns"] = len(df.columns)
                metadata["column_names"] = list(df.columns)
                metadata["error_message"] = "Dataset contains columns but no data rows (empty dataset)."
            else:
                metadata["error_message"] = "Uploaded dataset is completely empty."
            log_event("WARNING", "LOAD", metadata["error_message"])
            return df, metadata

        # Populate populated metadata
        metadata["rows"] = int(len(df))
        metadata["columns"] = int(len(df.columns))
        metadata["column_names"] = [str(c) for c in df.columns]
        metadata["memory_kb"] = round(df.memory_usage(deep=True).sum() / 1024, 2)
        metadata["initial_missing_count"] = int(df.isna().sum().sum())
        metadata["initial_duplicate_count"] = int(df.duplicated().sum())
        metadata["success"] = True

        log_event("SUCCESS", "LOAD", f"Loaded '{metadata['file_name']}' successfully ({metadata['rows']} rows, {metadata['columns']} cols, {metadata['file_size_kb']} KB)")
        return df, metadata

    except Exception as e:
        err = f"Failed to load dataset: {str(e)}"
        metadata["error_message"] = err
        metadata["success"] = False
        log_event("ERROR", "LOAD", err)
        return None, metadata
