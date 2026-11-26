# Face-recognition test fixtures

Real photographs used ONLY to test the real enrollment + embedding
matching path (`src/cueliez/observations/face_recognition.py`).
No fixture image is ever enrolled, stored, or transmitted by CueLiez
itself; tests enroll in-memory and discard.

## Portraits (committed, public domain)

White House portraits, downloaded from the `face_recognition` example
set (ageitgey/face_recognition on GitHub, public-domain US government
photos) and Wikimedia Commons:

- `obama.jpg`, `obama2.jpg`, `obama3.jpg` — three different photos of
  Barack Obama (official portraits / address). `obama3.jpg` is the
  held-out probe; `obama.jpg` + `obama2.jpg` are the enrollment set.
- `biden.jpg`, `biden2.jpg` — two different photos of Joe Biden
  (different person; must NOT match an Obama enrollment).

## Models (NOT committed — download to run the face tests)

`models/` is git-ignored (87 MB of binaries). Download:

- `nn4.small2.v1.t7` (31 MB, OpenFace embeddings):
  https://storage.cmusatyalab.org/openface-models/nn4.small2.v1.t7
- `lbfmodel.yaml` (56 MB, 68-point facial landmarks):
  https://raw.githubusercontent.com/kurnianggoro/GSOC2017/master/data/lbfmodel.yaml

Install the optional extra first (OpenCV 4.10 is pinned because
OpenCV 5.x removed the Torch model importer):

```
python3 -m venv .venv-face-test
.venv-face-test/bin/pip install -e ".[face]"
.venv-face-test/bin/python -m pytest tests/test_track_b_face_recognition.py -q
```

Without the extra or the models, the face tests skip and the core
fails closed (`FaceRecognitionUnavailable`) instead of producing a
match score.
