from fastapi import FastAPI, HTTPException, Body, Request, Query
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

# -------------------------------
# Routes
# -------------------------------


@app.get("/get_openrouter_balance", summary="Openrouter balance")
def get_openrouter_balance():
    """
    Return total and spent amount in usd
    """

    url = "https://openrouter.ai/api/v1/credits"
    response = requests.get(url, headers={"Authorization": f"Bearer {app.state.token}"})
    response_data = response.json()
    total_credits = response_data["data"]["total_credits"]
    spent_credits = response_data["data"]["total_usage"]
    return {"total in usd": total_credits, "spent in usd": spent_credits}

@app.get("/get_openrouter_models", summary="OpenRouter models")
def get_openrouter_models(
    request: Request,
    category: str | None = Query(None, description="Optional model category")
):
    """
    Return models available at OpenRouter.
    You can limit results by category, e.g.:
    roleplay, programming, marketing, technology, science, translation,
    legal, finance, health, trivia, academia
    """
    url = "https://openrouter.ai/api/v1/models"
    if category:
        url += f"?category={category}"

    headers = {"Authorization": f"Bearer {request.app.state.token}"}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        return {"error": str(e)}



