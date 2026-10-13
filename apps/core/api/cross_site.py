from starlette.types import ASGIApp, Receive, Scope, Send

# Requests that change something. GETs only read, and SameSite already
# keeps the cookie off cross-site ones that matter.
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
# What browsers put in Sec-Fetch-Site when another site's page sends the
# request. "same-site" too: another subdomain of your own domain is still
# another site's code. Same-origin pages, typed addresses and tools like
# curl (no header) are let through.
REFUSED = {b"cross-site", b"same-site"}


class CrossSiteGuard:
    """Refuses changes sent by another website's page (CSRF), on top of SameSite cookies.

    A Bearer token (dev owner token, a Node) is never sent by a browser on
    its own, so those requests are left to the normal auth checks.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope["method"] in UNSAFE_METHODS:
            headers = dict(scope["headers"])
            if headers.get(b"sec-fetch-site") in REFUSED and b"authorization" not in headers:
                await refuse(send)
                return
        await self.app(scope, receive, send)


async def refuse(send: Send) -> None:
    body = b'{"detail":"Refused: this request came from another website"}'
    await send({
        "type": "http.response.start",
        "status": 403,
        "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())],
    })
    await send({"type": "http.response.body", "body": body})
