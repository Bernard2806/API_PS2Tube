from app.api.routes import health, media, sessions  # noqa: F401


def create_session(client):
    response = client.post("/api/v1/sessions")
    assert response.status_code == 201
    return response.json()


def add_urls(client, session_id, urls):
    return client.post(
        f"/api/v1/sessions/{session_id}/queue", json={"urls": urls}
    )


def test_create_session_generates_code_and_pair_url(client):
    data = create_session(client)
    assert len(data["code"]) == 6
    assert data["status"] == "idle"
    assert data["pair_url"].endswith(f"/s/{data['code']}")
    assert data["qr_url"].endswith(f"/api/v1/sessions/{data['id']}/qr.png")


def test_add_and_list_queue(client):
    session = create_session(client)
    response = add_urls(client, session["id"], ["https://youtu.be/dQw4w9WgXcQ"])
    assert response.status_code == 201
    items = response.json()
    assert len(items) == 1
    assert items[0]["status"] == "queued"
    assert items[0]["position"] == 0

    listing = client.get(f"/api/v1/sessions/{session['id']}/queue").json()
    assert len(listing) == 1


def test_rejects_non_youtube_url(client):
    session = create_session(client)
    response = add_urls(client, session["id"], ["https://vimeo.com/123"])
    assert response.status_code == 422


def test_reorder_queue(client):
    session = create_session(client)
    items = add_urls(
        client,
        session["id"],
        ["https://youtu.be/aaaaaaaaaaa", "https://youtu.be/bbbbbbbbbbb"],
    ).json()
    reversed_ids = [items[1]["id"], items[0]["id"]]
    response = client.post(
        f"/api/v1/sessions/{session['id']}/queue/reorder",
        json={"item_ids": reversed_ids},
    )
    assert response.status_code == 200
    reordered = [item["id"] for item in response.json()]
    assert reordered == reversed_ids


def test_delete_item(client):
    session = create_session(client)
    item = add_urls(client, session["id"], ["https://youtu.be/aaaaaaaaaaa"]).json()[0]
    response = client.delete(
        f"/api/v1/sessions/{session['id']}/queue/{item['id']}"
    )
    assert response.status_code == 204
    assert client.get(f"/api/v1/sessions/{session['id']}/queue").json() == []


def test_next_is_204_until_ready(client):
    session = create_session(client)
    add_urls(client, session["id"], ["https://youtu.be/aaaaaaaaaaa"])
    response = client.get(f"/api/v1/sessions/{session['id']}/next")
    assert response.status_code == 204


def test_play_now_sets_current(client):
    session = create_session(client)
    items = add_urls(
        client,
        session["id"],
        ["https://youtu.be/aaaaaaaaaaa", "https://youtu.be/bbbbbbbbbbb"],
    ).json()
    response = client.post(
        f"/api/v1/sessions/{session['id']}/queue/{items[1]['id']}/play"
    )
    assert response.status_code == 200
    assert response.json()["current_item"]["id"] == items[1]["id"]


def test_complete_advances_to_next(client):
    session = create_session(client)
    items = add_urls(
        client,
        session["id"],
        ["https://youtu.be/aaaaaaaaaaa", "https://youtu.be/bbbbbbbbbbb"],
    ).json()
    client.post(f"/api/v1/sessions/{session['id']}/queue/{items[0]['id']}/play")
    response = client.post(f"/api/v1/sessions/{session['id']}/complete")
    assert response.json()["current_item"]["id"] == items[1]["id"]


def test_qr_returns_png(client):
    session = create_session(client)
    response = client.get(f"/api/v1/sessions/{session['id']}/qr.png")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content.startswith(b"\x89PNG\r\n\x1a\n")


def test_lookup_by_code(client):
    session = create_session(client)
    response = client.get(f"/api/v1/sessions/code/{session['code']}")
    assert response.status_code == 200
    assert response.json()["id"] == session["id"]


def test_unknown_session_returns_404(client):
    assert client.get("/api/v1/sessions/nope").status_code == 404
    assert client.get("/api/v1/sessions/code/ZZZZZZ").status_code == 404


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "ffmpeg" in body
    assert "yt_dlp" in body


def test_mobile_page_served(client):
    session = create_session(client)
    response = client.get(f"/s/{session['code']}")
    assert response.status_code == 200
    assert "PS2Tube" in response.text
