FROM mcr.microsoft.com/vscode/devcontainers/python:0-3.9

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
    && rm -rf /var/lib/apt/lists/* \
    && source /usr/local/share/nvm/nvm.sh \
    && nvm install 16 \
    && pip install --upgrade wheel pip

# Install some npm packages globally
RUN npm install -g ts-node

# Copy and install hactl - HA setup & run helper
RUN --mount=type=cache,target=/root/.cache pip install poetry poethepoet
COPY hactl /opt/hactl
RUN --mount=type=cache,target=/root/.cache cd /opt/hactl && poetry install && ln -s /opt/hactl/.venv/bin/hactl /usr/bin/hactl && mkdir /etc/hactl

# Install Home Assitant
COPY 01-defaults.yml /etc/hactl/
RUN mkdir -p /opt/hass
RUN --mount=type=cache,target=/root/.cache hactl setup

EXPOSE 8123

VOLUME /config
USER vscode
CMD sudo hactl configure && sudo hactl run
