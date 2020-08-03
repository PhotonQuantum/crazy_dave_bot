from asyncio import sleep

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

current_version = next_version = 1


async def infer(request: Request):
    print(request.query_params)
    await sleep(1)
    return JSONResponse({"sentence": request.query_params["sentence"], "response": "阿巴阿巴"})


async def inc_version(request: Request):
    global next_version
    next_version += 1
    return JSONResponse({"current": current_version, "next": next_version})


async def update(request: Request):
    print("update")
    global current_version
    if current_version == next_version:
        return JSONResponse({"updated": False, "version": current_version})
    old_version, current_version = current_version, next_version
    return JSONResponse({"updated": True, "version": current_version, "old": old_version})


app = Starlette(routes=[Route("/infer", infer), Route("/inc_version", inc_version), Route("/update", update)])
