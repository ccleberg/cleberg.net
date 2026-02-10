FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive \
    HOMEBREW_NO_AUTO_UPDATE=1 \
    PATH="/home/linuxbrew/.linuxbrew/bin:${PATH}"

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    procps \
    build-essential \
    ca-certificates \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash linuxbrew && \
    echo "linuxbrew:linuxbrew" | chpasswd && \
    adduser linuxbrew sudo

USER linuxbrew
WORKDIR /home/linuxbrew

RUN /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

RUN brew install emacs rsync uv minify

RUN mkdir -p ~/.config/emacs/.local/straight/repos && \
    git clone https://github.com/emacsorphanage/htmlize.git ~/.config/emacs/.local/straight/repos/htmlize && \
    git clone https://github.com/emacs-love/templatel.git ~/.config/emacs/.local/straight/repos/templatel && \
    git clone https://github.com/emacs-love/weblorg.git ~/.config/emacs/.local/straight/repos/weblorg

USER root
WORKDIR /builds
