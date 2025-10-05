import uvicorn
from fastapi import FastAPI
from chatbot.bot import app as chatbot_app
from airqualityapp.main2 import app as airquality_app
from airmonitor.main3 import app as airmonitor_app
from fastapi.middleware.cors import CORSMiddleware  

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],    
)

# Healthcheck endpoint para Railway
@app.get("/health")
def health_check():
    return {"status": "healthy", "message": "API is running"}

@app.get("/")
def root():
    return {
        "message": "🌍 NASA Air Quality API",
        "status": "online",
        "endpoints": {
            "chatbot": "/chatbot",
            "air_quality": "/airquality",
            "air_monitor": "/airmonitor",
            "docs": "/docs"
        }
    }

app.include_router(chatbot_app, prefix="/chatbot", tags=["Chatbot"])
app.include_router(airquality_app, prefix="/airquality", tags=["Air Quality"])
app.include_router(airmonitor_app, prefix="/airmonitor", tags=["Air Monitor"])


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)