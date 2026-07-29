import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import uuid
import asyncio
import logging
from datetime import datetime, timezone, timedelta

from app.models.lead import Lead, LeadStatus, LeadSource
from app.services.lead_service import process_lead, get_all_leads, get_lead_by_id, get_stats
from app.log_utils import ISO8601Formatter

# 配置 logging
logger = logging.getLogger("fastapi")
handler = logging.StreamHandler()
handler.setFormatter(ISO8601Formatter('%(asctime)s [%(levelname)s] %(message)s'))
logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False

# FastAPI app instance
app = FastAPI(title="RouteLeadAI - 识途线索AI", version="v2.0")

# CORS middleware for cross-origin requests
# 开发环境允许所有来源；生产环境应替换为具体域名
DEV_CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=DEV_CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic model for incoming lead data
class LeadIn(BaseModel):
    source: LeadSource
    raw_content: Optional[str] = None
    company_name: Optional[str] = None
    contact_name: Optional[str] = None
    position: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

@app.get("/")
async def root():
    return {"message": "Welcome to AI Sales Follow-up System"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Endpoint to receive leads
@app.post("/leads")
async def receive_lead(lead_in: LeadIn):
    # Convert to Lead model
    lead = Lead(
        source=lead_in.source,
        raw_content=lead_in.raw_content,
        company_name=lead_in.company_name,
        contact_name=lead_in.contact_name,
        email=lead_in.email,
        phone=lead_in.phone
    )
    try:
        # Process lead through classifier and router, push to Redis queue
        result = await process_lead(lead)
        logger.info(f"Lead processed successfully: {lead.id}")
        logger.info(f"Lead queued for async processing (intent_score={lead.intent_score})")
        return result
    except Exception as e:
        logger.error(f"Error processing lead {lead.id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process lead: {str(e)}")


@app.get("/leads")
async def list_leads():
    """List all leads"""
    try:
        leads = await get_all_leads()
        return {"total": len(leads), "leads": leads}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list leads: {str(e)}")


@app.get("/leads/{lead_id}")
async def get_lead(lead_id: str):
    """Get single lead by ID"""
    try:
        lead = await get_lead_by_id(lead_id)
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        return lead
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get lead: {str(e)}")


@app.get("/stats")
async def stats():
    """Get lead statistics"""
    try:
        return await get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")
