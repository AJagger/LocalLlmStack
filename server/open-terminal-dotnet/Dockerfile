# Construct an Open Terminal image with access to .NET tools
FROM ghcr.io/open-webui/open-terminal:0.15.5
USER root

# Add Microsoft's package source for the Debian release in the base image,
# then install the .NET 10 SDK (which includes the runtimes needed to run apps).
RUN set -eux; \
    . /etc/os-release; \
    curl -fsSL "https://packages.microsoft.com/config/debian/${VERSION_ID}/packages-microsoft-prod.deb" \
        -o /tmp/packages-microsoft-prod.deb; \
    dpkg -i /tmp/packages-microsoft-prod.deb; \
    rm /tmp/packages-microsoft-prod.deb; \
    apt-get update; \
    apt-get install -y --no-install-recommends dotnet-sdk-10.0; \
    rm -rf /var/lib/apt/lists/*

ENV DOTNET_ROOT=/usr/share/dotnet
ENV PATH="${DOTNET_ROOT}:${PATH}"

# Keep interactive/model-run commands under Open Terminal's normal user.
USER user
