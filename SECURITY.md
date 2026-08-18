# Security Policy

## 1. Reporting Security Issues

We take the security of ScrollSense seriously. If you discover a potential vulnerability or security concern, please report it responsibly:

- **Reporting Mechanism**: Report privately via GitHub Security Advisories by opening a confidential report under the repository's [Security Advisories](https://github.com/ak-bharadwaj/scrollsense/security/advisories/new) tab.
- **Details to Include**:
  - Description of the vulnerability.
  - Steps to reproduce or proof-of-concept.
  - Potential impact on users or infrastructure.
- **Response Timeline**: Maintainers will review and acknowledge receipt via GitHub Security Advisories within 48 hours and provide remediation status updates.

Please do **not** file public issues or discussions for vulnerabilities until a fix has been coordinated and released.

---

## 2. API Key and Secret Management

- **No Secrets in Source Control**: Never commit API keys (`GEMINI_API_KEY`, `GOOGLE_API_KEY`, etc.), tokens, or secrets to the git repository.
- **Environment Isolation**: Always manage secrets using runtime environment variables or `.env` files that are strictly listed in `.gitignore`.
- **Graceful Fallback**: The ScrollSense engine is designed to operate completely offline with deterministic signal extraction whenever external API credentials are absent.

---

## 3. Media Path Containment & File Security

- **Path Traversal Protection**: Media streaming routes enforce strict containment checks (`Path.resolve()` against accepted media root) to prevent directory traversal attacks (e.g. `../` escapes).
- **Filename Validation**: Reel IDs and filenames are validated against a strict alphanumeric whitelist regex (`^[a-zA-Z0-9_-]+$`).
- **MIME & Header Safety**: Media streaming endpoints serve binary assets with explicit MIME headers (`video/mp4`) and CORS restrictions.

---

## 4. Dependency Security & Auditing

- Dependencies are version-constrained in `pyproject.toml` to prevent uncontrolled transitive resolution.
- Regular security audits (`pip audit` / GitHub Dependabot) should be executed to identify vulnerable packages.

---

## 5. Production Deployment Considerations

- **CORS Configuration**: Restrict allowed CORS origins via `SCROLLSENSE_CORS_ORIGINS` to trusted frontend domains in production. Avoid wildcard (`*`) origins when handling authenticated requests.
- **Rate Limiting & Throttling**: Configure reverse proxies or API gateways to enforce request rate limiting on recommendation endpoints.
- **TLS/HTTPS**: Always terminate TLS/HTTPS at the load balancer or cloud platform (e.g. Cloud Run, Render) in production environments.
