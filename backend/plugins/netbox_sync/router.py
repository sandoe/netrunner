import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class NetboxConfig(BaseModel):
    url: str
    token: str


@router.post("/devices", summary="Pull Device data from NetBox")
async def get_netbox_devices(config: NetboxConfig):
    """
    Fetches device data from the provided NetBox URL.
    """
    headers = {"Authorization": f"Token {config.token}", "Accept": "application/json"}
    endpoint = f"{config.url.rstrip('/')}/api/dcim/devices/"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(endpoint, headers=headers, timeout=10.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code, detail=f"NetBox API error: {e}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to connect to NetBox: {e}"
            )


@router.post("/ips", summary="Pull IP data from NetBox")
async def get_netbox_ips(config: NetboxConfig):
    """
    Fetches IP address data from the provided NetBox URL.
    """
    headers = {"Authorization": f"Token {config.token}", "Accept": "application/json"}
    endpoint = f"{config.url.rstrip('/')}/api/ipam/ip-addresses/"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(endpoint, headers=headers, timeout=10.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code, detail=f"NetBox API error: {e}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to connect to NetBox: {e}"
            )
