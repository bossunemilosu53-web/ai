import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

app = FastAPI()

# Setup Rate Limiter (Max 5 requests per minute per user IP)
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Allowed Origins configured dynamically via environment variables
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://127.0.0.1:5500,http://localhost:5500").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GROQ_API_KEY = os.getenv("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")
MODEL_NAME = os.getenv("GROQ_MODEL", "qwen-2.5-32b")

class GenerateRequest(BaseModel):
    prompt: str

@app.get("/api/health")
def health_check():
    return {"status": "ok"}

@app.post("/api/generate")
@limiter.limit("5/minute")
async def generate(request: Request, req: GenerateRequest):
    if not GROQ_API_KEY:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY is not configured on server")
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": req.prompt}],
        "temperature": 0.7
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30.0
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=response.text)
                
            data = response.json()
            ai_response = data["choices"][0]["message"]["content"]
            return {"response": ai_response}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))