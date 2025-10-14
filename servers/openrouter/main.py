from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware


from pydantic import BaseModel, Field
from typing import Literal
from dotenv import load_dotenv
import pytz
import requests
import os

load_dotenv()

app = FastAPI(
    title="Fetch and return openrouter costs",
    version="1.0.0",
    description="Return total money spent on llm api requests",
)

token = os.getenv("API_TOKEN")
headers = {"Authorization": f"Bearer {token}"}

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------------
# Pydantic models
# -------------------------------



# -------------------------------
# Routes
# -------------------------------


@app.get("/get_openrouter_balance", summary="Openrouter balance")
def get_openrouter_balance():
    """
    Returns total openrouter balance and amount spent on llm queries.
    """
    url = "https://openrouter.ai/api/v1/credits"
    response = requests.get(url, headers=headers)
    response_data = response.json()
    total_credits = response_data["data"]["total_credits"]
    spent_credits = response_data["data"]["total_usage"]
    return {"total": total_credits, "spent": spent_credits}

