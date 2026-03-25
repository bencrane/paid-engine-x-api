from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from app.db.supabase import get_supabase_client
from app.shared.errors import NotFoundError

router = APIRouter(prefix="/lp", tags=["landing_pages"])


def _get_asset_by_slug(slug: str):
    supabase = get_supabase_client()
    res = (
        supabase.table("generated_assets")
        .select("id, content_url, input_data, template_used")
        .eq("slug", slug)
        .maybe_single()
        .execute()
    )
    if not res.data:
        raise NotFoundError(detail="Landing page not found")
    return res.data


@router.get("/{slug}", response_class=HTMLResponse)
async def serve_landing_page(slug: str):
    """Serve a published landing page by its slug."""
    asset = _get_asset_by_slug(slug)
    content_url = asset["content_url"]

    # Fetch the HTML from storage
    import httpx

    async with httpx.AsyncClient() as client:
        resp = await client.get(content_url)
        resp.raise_for_status()

    return HTMLResponse(content=resp.text, status_code=200)


@router.post("/{slug}/submit")
async def submit_landing_page_form(slug: str, request: Request):
    """Handle form submission from a landing page."""
    asset = _get_asset_by_slug(slug)
    body = await request.json()

    # Store submission in Supabase
    supabase = get_supabase_client()
    supabase.table("landing_page_submissions").insert({
        "asset_id": asset["id"],
        "slug": slug,
        "form_data": body,
    }).execute()

    return JSONResponse(
        content={"status": "ok", "message": "Form submitted successfully"},
        status_code=200,
    )
