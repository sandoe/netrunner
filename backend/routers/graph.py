"""Graph visualization API endpoint."""

from fastapi import APIRouter
from ..core.db import load_nodes_db, load_links_db

router = APIRouter()


@router.get("/graph")
async def get_graph():
    nodes_dict = await load_nodes_db()
    links_dict = await load_links_db()

    return {"nodes": list(nodes_dict.values()), "links": list(links_dict.values())}
