FROM python:3.13-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends git ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .
RUN pip install -e .

VOLUME /vaults
EXPOSE 8080

ENTRYPOINT ["python", "-m", "obsidian_vault_mcp"]
