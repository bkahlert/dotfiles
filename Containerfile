# base: what `make integration` runs. One-shot: the entrypoint applies the dotfiles and exits,
# so there is no service contract to probe (Podman warns that OCI images drop the directive).
# Pinned by digest on Docker Hub, where Dependabot bumps tag and digest together. Fully qualified because Podman
# maps a bare `fedora` to registry.fedoraproject.org, whose digest differs.
FROM docker.io/library/fedora:44@sha256:43b29f65a41eb9c35e1cd5323e3bdf3b655c2357a9f4f1ff2f9c2798e5045d80 AS base

# pipefail: a failed pipeline stage fails the build instead of passing on empty output.
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN dnf install -y zsh git curl jq findutils procps-ng unzip \
    && dnf clean all

# The tools below stay on latest: the weekly CI run exists to catch upstream drift.
# Each installer is downloaded to a file first, so a failed download stops the build.
RUN curl -fsSL --proto '=https' https://get.chezmoi.io -o /tmp/install.sh \
    && sh /tmp/install.sh -b /usr/local/bin \
    && rm /tmp/install.sh

RUN curl -fsSL --proto '=https' https://rossmacarthur.github.io/install/crate.sh -o /tmp/install.sh \
    && bash /tmp/install.sh --repo rossmacarthur/sheldon --to /usr/local/bin \
    && rm /tmp/install.sh

RUN curl -fsSL --proto '=https' https://starship.rs/install.sh -o /tmp/install.sh \
    && sh /tmp/install.sh --yes \
    && rm /tmp/install.sh

RUN curl -fsSL --proto '=https' https://raw.githubusercontent.com/ajeetdsouza/zoxide/main/install.sh -o /tmp/install.sh \
    && sh /tmp/install.sh \
    && rm /tmp/install.sh

RUN curl -fsSL --proto '=https' https://fnm.vercel.app/install -o /tmp/install.sh \
    && bash /tmp/install.sh --skip-shell --install-dir /usr/local/bin \
    && rm /tmp/install.sh

RUN chsh -s /bin/zsh root

HEALTHCHECK NONE

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]

# vnc: manual inspection of the applied shell in Ghostty; `make run` and `make vnc`.
FROM base AS vnc

RUN dnf install -y tigervnc-server fluxbox xterm \
    && dnf clean all

# Ghostty via the COPR the Ghostty docs recommend (https://ghostty.org/docs/install/binary#fedora).
RUN dnf install -y 'dnf-command(copr)' \
    && dnf copr enable -y scottames/ghostty \
    && dnf install -y ghostty \
    && dnf clean all

RUN mkdir -p /root/.vnc \
    && echo "password" | vncpasswd -f > /root/.vnc/passwd \
    && chmod 600 /root/.vnc/passwd

EXPOSE 5901
