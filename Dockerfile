# Reproducible static site build + offline verification container for Agora.
# Renders all pages deterministically from JSON task object artifacts and runs make check.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    make \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
COPY . /workspace

RUN python3 scripts/build_site.py --check && make check

CMD ["make", "check"]
