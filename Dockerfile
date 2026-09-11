FROM python:3.12-slim@sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN pip install --no-cache-dir uv

WORKDIR /app

# Install dependencies first so this layer is cached as long as
# pyproject.toml / uv.lock don't change (source changes shouldn't
# trigger a full dependency reinstall). Mirrors studylife-mcp's Dockerfile.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# hatch-vcs derives the package version from git tags, but this image never COPYs .git
# (deliberately, to keep the dependency layer above cacheable across releases) - so
# building the project itself below has no VCS history to read. CI passes the exact
# semantic-release version it already computed as a build-arg (see the docker job in
# ci.yml). Un-suffixed SETUPTOOLS_SCM_PRETEND_VERSION, not the dist-specific
# _FOR_STUDYLIFE_DISCORD variant - hatch-vcs's own get_version() call never sets
# dist_name, so the dist-specific form is silently never read (same finding as
# studylife-mcp's/studylife-alexa's Dockerfile).
ARG PACKAGE_VERSION=0.0.0+unknown
ENV SETUPTOOLS_SCM_PRETEND_VERSION=${PACKAGE_VERSION}

COPY README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev

# No data directory needed - unlike studylife-alexa/studylife-mcp, this bot holds no
# SQLite store: the single StudyLife API key lives in an env var (login.py writes it to
# a local .env at bootstrap time, never inside the container), and every command handler
# is a stateless read/write against StudyLife's own API.
RUN useradd --create-home --uid 1000 appuser
USER appuser

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["uvicorn", "studylife_discord.main:app", "--host", "0.0.0.0", "--port", "8000"]
