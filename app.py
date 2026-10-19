# nudenet-svc — HTTP wrapper around NudeNet (https://github.com/notAI-tech/NudeNet)
# Copyright (C) 2026 the nudenet-svc authors
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by the
# Free Software Foundation, either version 3 of the License, or (at your
# option) any later version. See LICENSE.
#
# AGPL-3.0 section 13: GET /source tells every network user where the
# Corresponding Source of the running version is.
"""
Stateless object detector over HTTP.

    POST /v1/detect   body = one image (image/jpeg, image/png, image/webp; max 8 MB)
                      -> {model, service, width, height, detections: [{label, score, box}], ms}
    GET  /healthz     -> {ok, model, loaded}
    GET  /source      -> {license, url, commit, upstream}

Nothing is written to disk and image contents are never logged.
"""
import hashlib
import os
from contextlib import asynccontextmanager
import threading
import time

import cv2
import numpy as np
import onnxruntime as ort
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from nudenet import NudeDetector

SERVICE = "nudenet-svc 1.0.0"
MODEL_PATH = os.environ.get("NUDENET_MODEL_PATH", "/models/640m.onnx")
MODEL_RES = int(os.environ.get("NUDENET_RESOLUTION", "640"))
MODEL_TAG = os.environ.get("NUDENET_MODEL_TAG", "nudenet-640m@v3.4-weights")
MODEL_SHA256 = os.environ.get("NUDENET_MODEL_SHA256", "")
THREADS = int(os.environ.get("NUDENET_THREADS", "2"))
MAX_BYTES = int(os.environ.get("NUDENET_MAX_BYTES", str(8 * 1024 * 1024)))
MIN_SCORE = float(os.environ.get("NUDENET_MIN_SCORE", "0.2"))
SOURCE_URL = os.environ.get("SOURCE_URL", "")
SOURCE_COMMIT = os.environ.get("SOURCE_COMMIT", "")
UPSTREAM = "https://github.com/notAI-tech/NudeNet (AGPL-3.0), weights v3.4-weights"

_detector = None
_lock = threading.Lock()   # one inference at a time: predictable memory & CPU
_load_error = None


def _verify(path, expected):
    if not expected:
        return
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    if h.hexdigest() != expected:
        raise RuntimeError(f"model checksum mismatch for {path}")


def detector():
    global _detector, _load_error
    if _detector is None:
        with _lock:
            if _detector is None:
                try:
                    _verify(MODEL_PATH, MODEL_SHA256)
                    det = NudeDetector(model_path=MODEL_PATH, inference_resolution=MODEL_RES)
                    # Replace the default session (all cores) with a bounded one.
                    so = ort.SessionOptions()
                    so.intra_op_num_threads = THREADS
                    so.inter_op_num_threads = 1
                    det.onnx_session = ort.InferenceSession(MODEL_PATH, so, providers=["CPUExecutionProvider"])
                    det.input_name = det.onnx_session.get_inputs()[0].name
                    _detector = det
                    _load_error = None
                except Exception as e:  # reported by /healthz and as 503
                    _load_error = str(e)
                    raise
    return _detector


@asynccontextmanager
async def lifespan(_app):
    try:
        detector()   # load at start so the first request is not slow
    except Exception:
        pass         # reported by /healthz; retried on the next request
    yield


app = FastAPI(title="nudenet-svc", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)


def _error(status, code, message):
    return JSONResponse(status_code=status, content={"error": code, "message": message})


@app.get("/healthz")
def healthz():
    return {"ok": _detector is not None, "model": MODEL_TAG, "loaded": _detector is not None,
            "service": SERVICE, **({"error": _load_error} if _load_error else {})}


@app.get("/source")
def source():
    return {"license": "AGPL-3.0-or-later", "url": SOURCE_URL, "commit": SOURCE_COMMIT, "upstream": UPSTREAM}


@app.post("/v1/detect")
async def detect(request: Request):
    length = request.headers.get("content-length")
    if length is not None and int(length) > MAX_BYTES:
        return _error(413, "too_large", f"image larger than {MAX_BYTES} bytes")
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > MAX_BYTES:
            return _error(413, "too_large", f"image larger than {MAX_BYTES} bytes")
    if not body:
        return _error(400, "empty", "request body must be an image")
    mat = cv2.imdecode(np.frombuffer(bytes(body), np.uint8), cv2.IMREAD_COLOR)
    if mat is None:
        return _error(400, "bad_image", "body is not a decodable image")
    try:
        det = detector()
    except Exception as e:
        return _error(503, "model_unavailable", str(e))
    t0 = time.perf_counter()
    with _lock:
        found = det.detect(mat)
    ms = round((time.perf_counter() - t0) * 1000)
    detections = [
        {"label": d["class"], "score": round(float(d["score"]), 4), "box": [int(v) for v in d["box"]]}
        for d in sorted(found, key=lambda d: -d["score"]) if d["score"] >= MIN_SCORE
    ]
    return {"model": MODEL_TAG, "service": SERVICE, "width": int(mat.shape[1]), "height": int(mat.shape[0]),
            "detections": detections, "ms": ms}
