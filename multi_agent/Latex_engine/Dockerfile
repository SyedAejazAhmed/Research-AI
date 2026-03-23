# LaTeX Compiler Docker Image
# Based on TeX Live 2024 for deterministic builds

FROM texlive/texlive:TL2024-historic

# Disable shell escape for security
ENV SHELL=/bin/false

# Set working directory
WORKDIR /work

# Install required packages
RUN tlmgr update --self && \
    tlmgr install \
    IEEEtran \
    llncs \
    acmart \
    cite \
    hyperref \
    graphicx \
    amsmath \
    amssymb \
    biber \
    biblatex

# Create entrypoint script
RUN echo '#!/bin/bash\n\
set -e\n\
cd /work\n\
exec "$@"' > /entrypoint.sh && \
    chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

# Default command: compile with pdflatex
CMD ["pdflatex", "-interaction=nonstopmode", "-shell-escape=false"]
