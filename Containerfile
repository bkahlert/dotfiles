FROM fedora:latest

# System packages
RUN dnf install -y \
      zsh git curl jq findutils procps-ng \
      tigervnc-server fluxbox xterm \
    && dnf clean all

# Install Ghostty via COPR
RUN dnf install -y 'dnf-command(copr)' \
    && dnf copr enable -y pgdev/ghostty \
    && dnf install -y ghostty \
    && dnf clean all

# Install chezmoi
RUN sh -c "$(curl -fsLS get.chezmoi.io)" -- -b /usr/local/bin

# Install Sheldon
RUN curl --proto '=https' -fLsS https://rossmacarthur.github.io/install/crate.sh \
    | bash -s -- --repo rossmacarthur/sheldon --to /usr/local/bin

# Install Starship
RUN curl -sS https://starship.rs/install.sh | sh -s -- --yes

# Install zoxide
RUN curl -sSfL https://raw.githubusercontent.com/ajeetdsouza/zoxide/main/install.sh | sh

# VNC setup
RUN mkdir -p /root/.vnc \
    && echo "password" | vncpasswd -f > /root/.vnc/passwd \
    && chmod 600 /root/.vnc/passwd

# Default shell
RUN chsh -s /bin/zsh root

EXPOSE 5901

# Entrypoint: apply dotfiles and start shell
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
