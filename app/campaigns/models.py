from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class CampaignSchedule(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class CampaignCreate(BaseModel):
    name: str
    description: Optional[str] = None
    platforms: list[str]
    audience_segment_id: Optional[str] = None
    budget: Optional[Decimal] = None
    schedule: Optional[CampaignSchedule] = None
    angle: Optional[str] = None
    objective: Optional[str] = None


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    platforms: Optional[list[str]] = None
    audience_segment_id: Optional[str] = None
    budget: Optional[Decimal] = None
    schedule: Optional[CampaignSchedule] = None
    angle: Optional[str] = None
    objective: Optional[str] = None


class CampaignResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    description: Optional[str] = None
    status: str
    platforms: list[str]
    audience_segment_id: Optional[str] = None
    budget: Optional[Decimal] = None
    schedule: Optional[CampaignSchedule] = None
    angle: Optional[str] = None
    objective: Optional[str] = None
    tracked_link_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class CampaignListResponse(BaseModel):
    data: list[CampaignResponse]
    total: int
