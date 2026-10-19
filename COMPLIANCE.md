# Licence compliance notes

Not legal advice. This file records how this service is kept separate from the
programs that call it, and what is owed under the AGPL. Have it reviewed by
counsel before relying on it.

## What is AGPL here

- **NudeNet** (`notAI-tech/NudeNet`): the GitHub repository is AGPL-3.0. The PyPI
  metadata of `nudenet` 3.4.2 says MIT; the stricter licence is assumed.
- **Model weights** `640m.onnx` (release `v3.4-weights`): trained with Ultralytics
  YOLOv8. Ultralytics states that trained models are covered by AGPL-3.0 unless
  an Enterprise licence is bought; this is disputed but assumed to apply.
- **This service** (`app.py`, `fetch_model.py`, Dockerfile) is therefore
  released under AGPL-3.0-or-later.

Dependencies under permissive licences: `onnxruntime` (MIT), `opencv-python-headless`
(Apache-2.0), `numpy` (BSD), `fastapi` (MIT), `uvicorn` (BSD). The `ultralytics`
package is not used.

## What we do

1. **Source is public** — the repository holding exactly what runs, including
   the Dockerfile. The image carries `org.opencontainers.image.source`,
   `.revision` and `.licenses` labels.
2. **AGPL §13 (remote network interaction)** — `GET /source` returns the
   repository URL and commit of the running build to anyone who can reach the
   service.
3. **Distribution** — whoever receives the image (e.g. an on-premise install)
   also receives the offer of the source above. Other programs shipped next to
   it are separate works (an "aggregate", AGPL §5) and are not affected.

## How callers stay separate programs

The FSF GPL FAQ treats programs that talk over sockets, pipes or command-line
arguments as normally separate, unless they exchange complex internal data
structures intimately. Accordingly:

- The service runs as its own process in its own container image, built from
  this repository only. Callers never import, link or copy NudeNet code or
  weights, and NudeNet's pre/post-processing is not reimplemented in callers.
- The interface is plain HTTP with generic data: an image file in, a list of
  `{label, score, box}` out (README "API"). Any other detector can implement
  the same interface; callers work without this service.
- The service is reached only over a private network (no published port).

## Open items

- Legal review of this approach before the results are used to make decisions
  visible to end customers.
- If counsel advises against relying on the "separate program" boundary:
  Ultralytics Enterprise licence, or a different detector behind the same API.
