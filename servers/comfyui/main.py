from fastapi import FastAPI, HTTPException, Body, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from io import BytesIO

from pydantic import BaseModel, Field
from typing import Literal
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

import pytz
import requests
import os
import base64


app = FastAPI(
    title="ComfyUI API Wrapper",
    version="1.0.0",
    description="Wrapper to allow interaction with ComfyUI",
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


@app.get("/generate_image", summary="Generate a image")
def generate_image():
    """
    Return total and spent amount in usd as a simple image
    """
    url = "https://openrouter.ai/api/v1/credits"
    response = requests.get(url, headers={"Authorization": f"Bearer {app.state.token}"})
    response_data = response.json()
    total_credits = response_data["data"]["total_credits"]
    spent_credits = response_data["data"]["total_usage"]
    
    # Create a simple image with text
    img = Image.new('RGB', (400, 200), color='white')
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 24)  # Use default font if unavailable
    except:
        font = ImageFont.load_default()
    
    draw.text((50, 50), f"Total: ${total_credits}", fill='black', font=font)
    draw.text((50, 100), f"Spent: ${spent_credits}", fill='black', font=font)
    
    # Save to bytes
    img_bytes = BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    encoded = base64.b64encode(img_bytes.getvalue()).decode('utf-8')
    return f"![Image of super mario](https://purepng.com/public/uploads/large/purepng.com-mariomariofictional-charactervideo-gamefranchisenintendodesigner-1701528634653vywuz.png)"



