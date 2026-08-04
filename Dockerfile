FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN python -m pip install --no-cache-dir .
RUN useradd --create-home --uid 10001 auditor && mkdir -p /app/.audit-reports && chown -R auditor:auditor /app/.audit-reports
USER auditor
EXPOSE 8765
ENTRYPOINT ["blockchain-auditor"]
CMD ["serve", "--host", "0.0.0.0", "--require-auth"]
