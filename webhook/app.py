from fastapi import FastAPI, Request, Form
from fastapi.responses import Response
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv
import logging
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_ROOT, ".env"))
sys.path.insert(0, _ROOT)

from bot.agent import chat

logging.basicConfig(level=logging.INFO)
app = FastAPI()

@app.post("/webhook")
async def webhook(
    request: Request,
    Body: str = Form(default=""),
    From: str = Form(default="")
):
    try:
        if not Body.strip():
            reply = "Please send a message."
        else:
            session_id = From.replace("whatsapp:", "")
            result = chat(session_id, Body.strip())
            reply = result["answer"]
            logging.info(
                f"session={session_id} | "
                f"scam={result.get('scam_type')} | "
                f"profile={result.get('profile')} | "
                f"engine={result.get('engine')}"
            )
    except Exception as e:
        logging.error(f"Error: {e}")
        reply = "Kuch gadbad ho gayi. Seedha 1930 pe call karein."

    resp = MessagingResponse()
    resp.message(reply.strip('"').strip("'"))
    return Response(content=str(resp), media_type="application/xml")

@app.get("/health")
async def health():
    return {"status": "ok", "cards": 75}
