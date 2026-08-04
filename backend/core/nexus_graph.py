import os
from gqlalchemy import Memgraph

MEMGRAPH_HOST = os.getenv("MEMGRAPH_HOST", "127.0.0.1")
MEMGRAPH_PORT = int(os.getenv("MEMGRAPH_PORT", 7687))

memgraph = Memgraph(MEMGRAPH_HOST, MEMGRAPH_PORT)


def get_memgraph():
    return memgraph
