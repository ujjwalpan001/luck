import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from database import db

app = FastAPI(
    title="CheatingPap Web App",
    description="A minimalist customer-admin message application.",
    version="1.0.0"
)

# Enable CORS for local testing/development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class MessageRequest(BaseModel):
    content: str



# API Endpoints
@app.get("/api/health")
async def health_check():
    """Endpoint for checking application active status."""
    return {"status": "ok", "message": "Backend is active"}

@app.post("/api/messages")
async def send_message(req: MessageRequest):
    """Save message sent from customer page."""
    content_stripped = req.content.strip()
    if not content_stripped:
        raise HTTPException(status_code=400, detail="Message content cannot be empty")
    
    try:
        saved_msg = await db.save_message(content_stripped)
        return {"status": "success", "message": saved_msg}
    except Exception as e:
        import logging
        logging.getLogger("main").error(f"Error saving message: {e}")
        raise HTTPException(status_code=503, detail="Database connection issue. Message could not be saved.")

@app.get("/api/messages")
async def get_messages():
    """Retrieve messages for the admin view."""
    try:
        messages = await db.get_messages()
        return {"status": "success", "messages": messages}
    except Exception as e:
        import logging
        logging.getLogger("main").error(f"Error getting messages: {e}")
        return {"status": "warning", "messages": [], "detail": "Database connection offline"}



# Serve Front-End Pages
@app.get("/")
async def serve_customer_page():
    """Serves the Customer HTML page."""
    file_path = os.path.join("static", "customer.html")
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return {"error": "customer.html not found"}

@app.get("/luckadmin")
async def serve_admin_page():
    """Serves the Admin HTML page."""
    file_path = os.path.join("static", "admin.html")
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return {"error": "admin.html not found"}

# Mount the static directory for CSS/assets (must be mounted after custom page routes to avoid masking them)
if not os.path.exists("static"):
    os.makedirs("static")

# We will mount static at /static so that stylesheets and scripts can be loaded
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    # Run server locally
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
