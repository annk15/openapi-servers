from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware

from forex_python.converter import CurrencyRates
from pydantic import BaseModel, Field
from typing import Literal
from dotenv import load_dotenv
import pytz
import requests
import os

app = FastAPI(
    title="Fetch data from OpenRouter",
    version="1.0.0",
    description="Fetch and return data from openrouter's api",
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
    app.state.token = os.getenv("API_TOKEN")
    print("Open Router token found!") 

# -------------------------------
# Pydantic models
# -------------------------------

def update_rates():
    rate = requests.get("https://api.frankfurter.app/latest", params={"base":"USD","symbols":"SEK"}, timeout=10).json()["rates"]["SEK"]
    print(rate)
    app.state.usd_sek_rate = rate
    print("Fetched exchange rate: " + str(rate)) 

# -------------------------------
# Routes
# -------------------------------


@app.get("/get_openrouter_balance", summary="Openrouter balance")
def get_openrouter_balance():
    """
    Return total and spent amount in sek
    """
    update_rates()
    url = "https://openrouter.ai/api/v1/credits"
    response = requests.get(url, headers={"Authorization": f"Bearer {app.state.token}"})
    response_data = response.json()
    total_credits = response_data["data"]["total_credits"]
    spent_credits = response_data["data"]["total_usage"]
    return {"total in kr": total_credits * app.state.usd_sek_rate, "spent in kr": spent_credits * app.state.usd_sek_rate}



