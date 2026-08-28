import json
import os
import glob

# Ensure ROOT_DIR is set up
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_latest_ingestion_folder() -> str:
    """
    Finds the most recent DI_RUN_n_<timestamp> folder in Data-Ingestion.
    """
    ingestion_dir = os.path.join(ROOT_DIR, "SAVE-DATA-PER-AGENT", "Data-Ingestion-Output")
    if not os.path.exists(ingestion_dir):
        raise FileNotFoundError(f"Data-Ingestion directory not found at {ingestion_dir}")
        
    runs = [d for d in os.listdir(ingestion_dir) if d.startswith("DI_RUN_") and os.path.isdir(os.path.join(ingestion_dir, d))]
    
    if not runs:
        raise FileNotFoundError("No DI_RUN folders found in Data-Ingestion")
        
    # Sort by the 'n' in DI_RUN_n_<timestamp>
    def extract_n(folder_name):
        parts = folder_name.split("_")
        if len(parts) >= 3:
            try:
                return int(parts[2])
            except ValueError:
                return -1
        return -1
        
    runs.sort(key=extract_n)
    return os.path.join(ingestion_dir, runs[-1])


def get_file_path(base_folder: str, symbol: str, data_type: str) -> str:
    """
    Constructs the path to the specific JSON file inside the run folder.
    """
    filepath = os.path.join(base_folder, data_type, f"{symbol}_{data_type}.json")
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Data file not found: {filepath}")
    return filepath


def load_latest_bars(symbol: str):
    base_folder = get_latest_ingestion_folder()
    filepath = get_file_path(base_folder, symbol, "bars")
    with open(filepath) as f:
        return json.load(f)


def load_latest_news(symbol: str):
    base_folder = get_latest_ingestion_folder()
    filepath = get_file_path(base_folder, symbol, "news")
    with open(filepath) as f:
        return json.load(f)


def load_latest_options(symbol: str):
    base_folder = get_latest_ingestion_folder()
    filepath = get_file_path(base_folder, symbol, "options")
    with open(filepath) as f:
        return json.load(f)


def get_latest_processing_folder() -> str:
    """
    Finds the most recent DP_RUN_n_<timestamp> folder in Data-Processing-Output.
    """
    processing_dir = os.path.join(ROOT_DIR, "SAVE-DATA-PER-AGENT", "Data-Processing-Output")
    if not os.path.exists(processing_dir):
        raise FileNotFoundError(f"Data-Processing-Output directory not found at {processing_dir}")
        
    runs = [d for d in os.listdir(processing_dir) if d.startswith("DP_RUN_") and os.path.isdir(os.path.join(processing_dir, d))]
    
    if not runs:
        raise FileNotFoundError("No DP_RUN folders found in Data-Processing-Output")
        
    def extract_n(folder_name):
        parts = folder_name.split("_")
        if len(parts) >= 3:
            try:
                return int(parts[2])
            except ValueError:
                return -1
        return -1
        
    runs.sort(key=extract_n)
    return os.path.join(processing_dir, runs[-1])


def load_latest_state(symbol: str):
    base_folder = get_latest_processing_folder()
    filepath = os.path.join(base_folder, f"{symbol}_state.json")
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"State file not found: {filepath}")
    with open(filepath) as f:
        return json.load(f)
