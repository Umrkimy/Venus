import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from api.cross_site import CrossSiteGuard

app = FastAPI()
app.add_middleware(CrossSiteGuard)


@app.api_route("/change", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
def change():
    return {"changed": True}


client = TestClient(app)


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
@pytest.mark.parametrize("site", ["cross-site", "same-site"])
def test_changes_from_another_site_are_refused(method: str, site: str):
    response = client.request(method, "/change", headers={"Sec-Fetch-Site": site})

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {"detail": "Refused: this request came from another website"}


@pytest.mark.parametrize("site", ["same-origin", "none", None])
def test_venus_pages_typed_addresses_and_tools_pass(site: str | None):
    # None: curl and the Node send no Sec-Fetch-Site at all.
    headers = {"Sec-Fetch-Site": site} if site else {}

    response = client.post("/change", headers=headers)

    assert response.status_code == status.HTTP_200_OK


def test_reading_is_never_blocked():
    response = client.get("/change", headers={"Sec-Fetch-Site": "cross-site"})

    assert response.status_code == status.HTTP_200_OK


def test_bearer_tokens_are_left_to_the_auth_checks():
    # A browser never adds a Bearer token by itself, so this isn't a CSRF.
    response = client.post(
        "/change", headers={"Sec-Fetch-Site": "cross-site", "Authorization": "Bearer x"}
    )

    assert response.status_code == status.HTTP_200_OK
