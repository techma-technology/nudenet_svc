# nudenet-svc — AGPL-3.0-or-later (see LICENSE)
"""API contract tests. Needs the real model: NUDENET_MODEL_PATH=/path/to/640m.onnx pytest -q"""
import os

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

if not os.path.exists(os.environ.get("NUDENET_MODEL_PATH", "/models/640m.onnx")):
    pytest.skip("model file not found (set NUDENET_MODEL_PATH)", allow_module_level=True)

os.environ.setdefault("NUDENET_MAX_BYTES", str(200_000))
import app as svc  # noqa: E402

client = TestClient(svc.app)


def jpeg(w=320, h=240, color=(40, 160, 90)):
    img = np.zeros((h, w, 3), np.uint8)
    img[:] = color
    cv2.circle(img, (w // 2, h // 2), min(w, h) // 4, (200, 200, 220), -1)
    return cv2.imencode(".jpg", img)[1].tobytes()


def test_healthz_reports_loaded_model():
    client.post("/v1/detect", content=jpeg(), headers={"Content-Type": "image/jpeg"})
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert r.json()["model"] == svc.MODEL_TAG


def test_detect_returns_contract_shape():
    r = client.post("/v1/detect", content=jpeg(), headers={"Content-Type": "image/jpeg"})
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"model", "service", "width", "height", "detections", "ms"}
    assert (body["width"], body["height"]) == (320, 240)
    for d in body["detections"]:
        assert set(d) == {"label", "score", "box"} and len(d["box"]) == 4
        assert d["score"] >= svc.MIN_SCORE


def test_png_is_accepted():
    png = cv2.imencode(".png", np.full((64, 64, 3), 255, np.uint8))[1].tobytes()
    assert client.post("/v1/detect", content=png, headers={"Content-Type": "image/png"}).status_code == 200


@pytest.mark.parametrize("body,code", [(b"", "empty"), (b"not an image at all", "bad_image")])
def test_bad_input_is_400(body, code):
    r = client.post("/v1/detect", content=body, headers={"Content-Type": "image/jpeg"})
    assert r.status_code == 400
    assert r.json()["error"] == code


def test_too_large_is_413():
    r = client.post("/v1/detect", content=b"\xff" * 300_000, headers={"Content-Type": "image/jpeg"})
    assert r.status_code == 413
    assert r.json()["error"] == "too_large"


def test_source_points_to_agpl_source():
    r = client.get("/source")
    assert r.status_code == 200
    assert r.json()["license"] == "AGPL-3.0-or-later"
    assert "NudeNet" in r.json()["upstream"]
