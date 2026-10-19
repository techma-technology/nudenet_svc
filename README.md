# nudenet-svc

A small, stateless HTTP service that runs the [NudeNet](https://github.com/notAI-tech/NudeNet)
detector (model `640m`, release `v3.4-weights`) and returns body-part labels with
scores and boxes. It keeps nothing: no disk writes, no database, image contents
are never logged.

Licensed under **AGPL-3.0-or-later**, like NudeNet itself (see `LICENSE` and
`COMPLIANCE.md`).

## API (v1)

| Method | Path | Result |
|---|---|---|
| `POST` | `/v1/detect` | body = one image (`image/jpeg`, `image/png`, `image/webp`; max 8 MB) → `{model, service, width, height, detections: [{label, score, box: [x, y, w, h]}], ms}` |
| `GET` | `/healthz` | `{ok, model, loaded, service}` |
| `GET` | `/source` | `{license, url, commit, upstream}` — where to get the source of the running version |

Errors: `400 {error: "empty" | "bad_image"}`, `413 {error: "too_large"}`,
`503 {error: "model_unavailable"}`. Detections below score 0.2 are dropped.

Labels: `FEMALE_GENITALIA_COVERED`, `FACE_FEMALE`, `BUTTOCKS_EXPOSED`,
`FEMALE_BREAST_EXPOSED`, `FEMALE_GENITALIA_EXPOSED`, `MALE_BREAST_EXPOSED`,
`ANUS_EXPOSED`, `FEET_EXPOSED`, `BELLY_COVERED`, `FEET_COVERED`,
`ARMPITS_COVERED`, `ARMPITS_EXPOSED`, `FACE_MALE`, `BELLY_EXPOSED`,
`MALE_GENITALIA_EXPOSED`, `ANUS_COVERED`, `FEMALE_BREAST_COVERED`,
`BUTTOCKS_COVERED`.

## Build & run

```sh
docker build -t nudenet-svc:1.0.0 \
  --build-arg SOURCE_URL=https://github.com/<owner>/nudenet-svc \
  --build-arg SOURCE_COMMIT=$(git rev-parse HEAD) .
docker run --rm -p 127.0.0.1:8000:8000 --read-only --tmpfs /tmp nudenet-svc:1.0.0
curl --data-binary @photo.jpg -H 'Content-Type: image/jpeg' http://127.0.0.1:8000/v1/detect
```

The model is downloaded from the upstream GitHub release during the build and
its SHA-256 is checked (`04fe3d77…34eb`, 103,538,690 bytes).

Environment: `NUDENET_THREADS` (2), `NUDENET_MAX_BYTES` (8 MB),
`NUDENET_MIN_SCORE` (0.2), `SOURCE_URL`, `SOURCE_COMMIT`.

Measured (x86, 2 threads): ±360 ms per image, +120 MB when the model is
loaded, ±350 MB process peak.

## Tests

```sh
pip install -r requirements.txt pytest httpx
NUDENET_MODEL_PATH=/path/to/640m.onnx pytest -q
```
