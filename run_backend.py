"""
Simple startup script for the backend server.
Sets PYTHONPATH and runs uvicorn.
"""
import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import uvicorn

if __name__ == "__main__":
    # Disable reload by default on Windows to avoid watchfiles hangs; opt-in via RELOAD=1.
    reload_enabled = os.getenv("RELOAD", "").lower() in {"1", "true", "yes", "on"}
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=reload_enabled,
    )
