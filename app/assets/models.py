from pydantic import BaseModel
from typing import Optional, Literal, Union


class BrandingConfig(BaseModel):
    logo_url: Optional[str] = None
    primary_color: str = "#00e87b"
    secondary_color: str = "#09090b"
    font_family: str = "Inter, sans-serif"
    company_name: str = ""


class TrackingConfig(BaseModel):
    rudderstack_write_key: Optional[str] = None
    rudderstack_data_plane_url: Optional[str] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None


class FormField(BaseModel):
    name: str
    label: str
    type: str = "text"
    required: bool = True


class Section(BaseModel):
    heading: str
    body: str
    bullets: Optional[list[str]] = None
    callout: Optional[str] = None


class MetricCallout(BaseModel):
    value: str
    label: str


class SocialProofConfig(BaseModel):
    type: Literal["logos", "quote", "stats"]
    logos: Optional[list[str]] = None
    quote_text: Optional[str] = None
    quote_author: Optional[str] = None
    quote_title: Optional[str] = None
    stats: Optional[list[MetricCallout]] = None


class LeadMagnetPageInput(BaseModel):
    template: Literal["lead_magnet_download"] = "lead_magnet_download"
    headline: str
    subhead: str
    value_props: list[str]
    form_fields: list[FormField]
    cta_text: str = "Download Now"
    branding: BrandingConfig
    tracking: TrackingConfig = TrackingConfig()
    social_proof: Optional[SocialProofConfig] = None
    hero_image_url: Optional[str] = None


class CaseStudyPageInput(BaseModel):
    template: Literal["case_study"] = "case_study"
    customer_name: str
    customer_logo_url: Optional[str] = None
    headline: str
    sections: list[Section]
    metrics: list[MetricCallout]
    quote_text: Optional[str] = None
    quote_author: Optional[str] = None
    quote_title: Optional[str] = None
    cta_text: str = "Get Similar Results"
    form_fields: list[FormField] = []
    branding: BrandingConfig
    tracking: TrackingConfig = TrackingConfig()


class WebinarPageInput(BaseModel):
    template: Literal["webinar"] = "webinar"
    event_name: str
    event_date: str
    headline: str
    speakers: list[dict]
    agenda: list[str]
    form_fields: list[FormField]
    cta_text: str = "Register Now"
    branding: BrandingConfig
    tracking: TrackingConfig = TrackingConfig()


class DemoRequestPageInput(BaseModel):
    template: Literal["demo_request"] = "demo_request"
    headline: str
    subhead: str
    benefits: list[Section]
    trust_signals: Optional[SocialProofConfig] = None
    form_fields: list[FormField]
    cta_text: str = "Request Demo"
    branding: BrandingConfig
    tracking: TrackingConfig = TrackingConfig()


LandingPageInput = Union[
    LeadMagnetPageInput, CaseStudyPageInput, WebinarPageInput, DemoRequestPageInput
]


class PDFSection(BaseModel):
    heading: str
    body: str
    bullets: Optional[list[str]] = None
    callout_box: Optional[str] = None


class LeadMagnetPDFInput(BaseModel):
    title: str
    subtitle: Optional[str] = None
    sections: list[PDFSection]
    branding: BrandingConfig


class Slide(BaseModel):
    headline: str
    body: Optional[str] = None
    stat_callout: Optional[str] = None
    stat_label: Optional[str] = None
    is_cta_slide: bool = False
    cta_text: Optional[str] = None


class DocumentAdInput(BaseModel):
    slides: list[Slide]
    branding: BrandingConfig
    aspect_ratio: Literal["1:1", "4:5"] = "1:1"
