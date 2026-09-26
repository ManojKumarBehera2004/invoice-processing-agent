import uvicorn
import os
from app.config import settings

if __name__ == "__main__":
    # Support PORT env variable for cloud deployment (e.g., Render, Heroku)
    port = int(os.environ.get("PORT", settings.APP_PORT))
    host = os.environ.get("HOST", settings.APP_HOST)
    
    print("=" * 60)
    print(f"🚀 {settings.APP_NAME}")
    print("=" * 60)
    print(f"👉 Dashboard:  http://localhost:{port}/dashboard")
    print(f"👉 Upload UI:   http://localhost:{port}/upload")
    print(f"👉 API Docs:    http://localhost:{port}/docs")
    print("=" * 60)
    print()
    uvicorn.run("app.main:app", host=host, port=port, reload=True)
