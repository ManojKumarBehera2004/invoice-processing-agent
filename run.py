import uvicorn
import os
from app.config import settings

if __name__ == "__main__":
    # Support PORT env variable for cloud deployment (e.g., Render, Heroku)
    port = int(os.environ.get("PORT", settings.APP_PORT))
    host = os.environ.get("HOST", settings.APP_HOST)
    
    print(f"Starting {settings.APP_NAME} at http://{host}:{port}")
    uvicorn.run("app.main:app", host=host, port=port, reload=True)
