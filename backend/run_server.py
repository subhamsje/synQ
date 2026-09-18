import os
import sys
import uvicorn

# Ensure repository root is in python path
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

if __name__ == "__main__":
    from backend.api.app import app
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
