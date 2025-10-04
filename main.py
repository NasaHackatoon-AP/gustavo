import uvicorn
from fastapi import FastAPI
from chatbot.bot import app as chatbot_app
from airqualityapp.main2 import app as airquality_app
from airmonitor.main3 import app as airmonitor_app

app = FastAPI()

app.include_router(chatbot_app, prefix="/chatbot", tags=["Chatbot"])
app.include_router(airquality_app, prefix="/airquality", tags=["Air Quality"])
app.include_router(airmonitor_app, prefix="/airmonitor", tags=["Air Monitor"])


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)