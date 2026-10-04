# base: what `make integration` runs. One-shot: the entrypoint applies the dotfiles and exits,
# so there is no service contract to probe (Podman warns that OCI images drop the directive).
FROM fedora:44 AS base

# pipefail: a failed pipeline stage fails the build instead of passing on empty output.
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN dnf install -y zsh git curl jq findutils procps-ng \
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
