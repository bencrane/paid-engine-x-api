import httpx

from app.config import settings

_STORAGE_BASE = f"{settings.SUPABASE_URL}/storage/v1"
_BUCKET = "assets"


async def _ensure_bucket():
    """Create the assets bucket if it doesn't exist (idempotent)."""
    headers = {
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{_STORAGE_BASE}/bucket",
            headers=headers,
            json={
                "id": _BUCKET,
                "name": _BUCKET,
                "public": True,
            },
        )
        # 200 = created, 409 = already exists — both fine
        if resp.status_code not in (200, 201, 409):
            resp.raise_for_status()


async def upload_asset(file_bytes: bytes, filename: str, content_type: str) -> str:
    """Upload to Supabase Storage, return public URL."""
    await _ensure_bucket()

    headers = {
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": content_type,
    }
    url = f"{_STORAGE_BASE}/object/{_BUCKET}/{filename}"

    async with httpx.AsyncClient() as client:
        # Try POST first; if file exists, use PUT to overwrite
        resp = await client.post(url, headers=headers, content=file_bytes)
        if resp.status_code == 400:
            resp = await client.put(url, headers=headers, content=file_bytes)
        resp.raise_for_status()

    public_url = f"{settings.SUPABASE_URL}/storage/v1/object/public/{_BUCKET}/{filename}"
    return public_url
