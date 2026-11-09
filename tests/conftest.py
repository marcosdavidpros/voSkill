import asyncio

import httpx

from voskill.main import app


class StateInjector:
    def __init__(self, application, state: dict[str, object]) -> None:
        self.application = application
        self.state = state

    async def __call__(self, scope, receive, send) -> None:
        scope.setdefault("state", {}).update(self.state)
        await self.application(scope, receive, send)


def _request(
    method: str,
    path: str,
    payload: dict | None = None,
    state: dict[str, object] | None = None,
) -> httpx.Response:
    async def send() -> httpx.Response:
        application = StateInjector(app, state) if state is not None else app
        transport = httpx.ASGITransport(app=application)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.request(method, path, json=payload)

    return asyncio.run(send())