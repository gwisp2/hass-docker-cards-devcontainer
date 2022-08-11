FROM mcr.microsoft.com/vscode/devcontainers/python:0-3.9

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

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
        supervisor \
    && rm -rf /var/lib/apt/lists/* \
    && source /usr/local/share/nvm/nvm.sh \
    && nvm install 16 \
    && pip install --upgrade wheel pip

# For running helper scripts
RUN npm install -g ts-node

EXPOSE 8123

VOLUME /config

# Download Home Assistant dependencies
# We need to install sqlalchemy and fnvhash due to the issue.
# https://github.com/home-assistant/core/issues/76296
RUN --mount=type=cache,target=/root/.cache pip install homeassistant==2022.8.3 sqlalchemy fnvhash

# Install TheToken custom component to generate a long-lived access token for running helper scripts
RUN git clone https://github.com/gwisp2/hass-the-token.git && \
    mkdir -p /config/custom_components && \
    cp -R hass-the-token/custom_components/the_token /config/custom_components/ && \
    rm -rf hass-the-token

# Copy supervisor configuration
RUN mkdir -p /var/log/supervisor
COPY supervisord.conf /etc/supervisord.conf

# Copy helper shell scripts
COPY hactl /usr/bin
COPY hassfest /usr/bin

USER vscode

# root is required to start supervisor and setup Home Assistant
CMD sudo -E hactl setup-run
