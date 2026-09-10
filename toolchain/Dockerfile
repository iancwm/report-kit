FROM debian:13-slim@sha256:d7e12182ce18b85b93007c1dedf31f2d29e01ccf3182cc4017c709b6259bc132

ARG DEBIAN_FRONTEND=noninteractive
RUN rm -f /etc/apt/sources.list.d/debian.sources \
 && printf '%s\n' \
      'deb [check-valid-until=no] https://snapshot.debian.org/archive/debian/20260901T000000Z trixie main contrib non-free non-free-firmware' \
      > /etc/apt/sources.list \
 && apt-get -o Acquire::Check-Valid-Until=false update \
 && apt-get install -y --no-install-recommends \
      ca-certificates=20250419 fontconfig=2.15.0-2.3 git=1:2.47.3-0+deb13u1 \
      pandoc=3.1.11.1+ds-2 \
      python3=3.13.5-1 python3-pip=25.1.1+dfsg-1 python3-venv=3.13.5-1 \
      texlive-bibtex-extra=2024.20250309-2 texlive-fonts-recommended=2024.20250309-1 \
      texlive-latex-extra=2024.20250309-2 texlive-luatex=2024.20250309-1 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/reportkit
COPY toolchain/requirements.lock /opt/reportkit/toolchain/requirements.lock
COPY font_data /opt/reportkit/font_data
RUN printf '%s  %s\n' \
      '2634cf36c3b193f2d9a026b023eda41bd2f013a508662f0a23bcafe5a3239c08' 'toolchain/requirements.lock' \
      'a0936e8e2b28f990fd0472c07a8db9128a874b40e79e87853585f08c8106f114' 'font_data/GoogleSans-Bold.ttf' \
      '4de69940330e5783c678b94809c68b44f1e4af544ae7d7638d3c659b83895867' 'font_data/GoogleSans-Medium.ttf' \
      '9bbea74c7b2717525b76f0631ca03574cf672030c64f3961e8d54bfe0bc4b68a' 'font_data/GoogleSans-Regular.ttf' \
      '3f02be1a2c269af8c5ea95b2b93a8337e8cc1147f17f8f607923e189939fa7c9' 'font_data/reportkit-libertinus-fonts.tar.gz' \
    | sha256sum --check --strict
RUN python3 -m venv /opt/reportkit/.venv \
 && /opt/reportkit/.venv/bin/pip install --no-cache-dir -r /opt/reportkit/toolchain/requirements.lock

COPY . /opt/reportkit
RUN install -d /usr/local/share/fonts/reportkit \
 && install -m 0644 font_data/GoogleSans-Bold.ttf font_data/GoogleSans-Medium.ttf \
      font_data/GoogleSans-Regular.ttf /usr/local/share/fonts/reportkit/ \
 && fc-cache -f \
 && mkdir -p /usr/local/share/texmf \
 && tar -xzf font_data/reportkit-libertinus-fonts.tar.gz -C /usr/local/share/texmf \
 && mktexlsr /usr/local/share/texmf

ENV PATH="/opt/reportkit/.venv/bin:${PATH}" \
    SOURCE_DATE_EPOCH=1 \
    TZ=UTC \
    PYTHONHASHSEED=0 \
    MPLBACKEND=Agg \
    REPORTKIT_TOOLCHAIN_FINGERPRINT=74513be7e9578e0bc9ec84bcb12a1edf43743a32b967ee6b8b8b4288e96fe50c

ENTRYPOINT ["/opt/reportkit/reportkit"]
