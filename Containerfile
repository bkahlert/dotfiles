# base: what `make integration` runs. One-shot: the entrypoint applies the dotfiles and exits,
# so there is no service contract to probe (Podman warns that OCI images drop the directive).
FROM fedora:latest AS base

RUN dnf install -y zsh git curl jq findutils procps-ng \
    && dnf clean all

RUN sh -c "$(curl -fsLS get.chezmoi.io)" -- -b /usr/local/bin

RUN curl --proto '=https' -fLsS https://rossmacarthur.github.io/install/crate.sh \
    | bash -s -- --repo rossmacarthur/sheldon --to /usr/local/bin

RUN curl -sS https://starship.rs/install.sh | sh -s -- --yes

RUN curl -sSfL https://raw.githubusercontent.com/ajeetdsouza/zoxide/main/install.sh | sh

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
