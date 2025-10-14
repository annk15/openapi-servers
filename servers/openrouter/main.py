from fastapi import FastAPI, HTTPException, Body, Request
from fastapi.middleware.cors import CORSMiddleware


from pydantic import BaseModel, Field
from typing import Literal
from dotenv import load_dotenv
import pytz
import requests
import os

app = FastAPI(
    title="Fetch and return openrouter costs",
    version="1.0.0",
    description="Return total money spent on llm api requests",
)

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    load_dotenv()
    token = os.getenv("API_TOKEN")
    app.state.headers = {"Authorization": f"Bearer {token}"}

# -------------------------------
# Pydantic models
# -------------------------------

def convert_to_sek(amount):
    c = CurrencyRates()
    rate = c.get_rate('USD', 'SEK')
    return amount * rate

# -------------------------------
# Routes
# -------------------------------


@app.get("/get_openrouter_balance", summary="Openrouter balance")
def get_openrouter_balance(request: Request):
    """
    Return total Openrouter balance and amount spent in sek.
    """
    url = "https://openrouter.ai/api/v1/credits"
    print(request.app.state.headers)
    response = requests.get(url, headers=request.app.state.headers)
    response_data = response.json()
    total_credits = response_data["data"]["total_credits"]
    spent_credits = response_data["data"]["total_usage"]
    return {"total": convert_to_sek(total_credits), "spent": convert_to_sek(spent_credits)}

