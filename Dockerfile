FROM mcr.microsoft.com/vscode/devcontainers/python:3.10-bullseye

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install nvm & pip & HA dependencies
RUN --mount=type=cache,target=/var/cache/apt \
    curl -sS https://dl.yarnpkg.com/debian/pubkey.gpg | apt-key add - \
    && apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        bluez \
        libudev-dev \
        libavformat-dev \
        libavcodec-dev \
        libavdevice-dev \
        libavutil-dev \
        libswscale-dev \
        libswresample-dev \
        libavfilter-dev \
        libpcap-dev \
        git \
        libffi-dev \
        libssl-dev \
        libjpeg-dev \
        zlib1g-dev \
        autoconf \
        build-essential \
        libopenjp2-7 \
        libtiff5 \
        libturbojpeg0 \
        tzdata \
        sqlite3 \
    && rm -rf /var/lib/apt/lists/* \
    && source /usr/local/share/nvm/nvm.sh \
    && nvm install 16 \
    && pip install --upgrade wheel pip

# Install some npm packages globally
RUN npm install --location=global ts-node

# Create directories owned by vscode
RUN install -d -m 0755 -o vscode -g vscode /henv /hdata /hactl /etc/hactl

# Do consequent setup with vscode user
USER vscode

# Temporarily install playwright, we can't install it globally because it requires root access,
# but npm drops root to 1001 user when running install scripts.
# Also because of that we need a sudoer user when installing browsers & dependencies for playwright.
RUN set -e; . /etc/profile; mkdir /tmp/playwright && cd /tmp/playwright && \
    npm install playwright && npx playwright install-deps && npx playwright install && rm -rf /tmp/playwright

# Copy and install hactl - HA setup & run helper
RUN --mount=type=cache,target=/home/root/.cache sudo -H pip install poetry poethepoet
COPY hactl /hactl
RUN --mount=type=cache,target=/home/vscode/.cache,uid=1000,gid=1000 cd /hactl && poetry install && sudo ln -s /hactl/.venv/bin/hactl /usr/bin/hactl

# Install Home Assitant
COPY 01-defaults.yml /etc/hactl/
RUN --mount=type=cache,target=/home/vscode/.cache,uid=1000,gid=1000 hactl setup

EXPOSE 8123

VOLUME /config
CMD hactl run
