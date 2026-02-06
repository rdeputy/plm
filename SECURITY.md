# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly:

1. **Do not** open a public GitHub issue
2. Email security concerns to the repository maintainer
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

## Security Measures

This project implements:

- API key and JWT authentication
- CORS configuration
- Input validation via Pydantic
- Secure password comparison (timing-attack resistant)
- Non-root Docker containers
- Environment-based configuration (no hardcoded secrets)

## Best Practices for Deployment

1. Always use HTTPS in production
2. Set strong API keys and JWT secrets
3. Configure restrictive CORS origins
4. Use PostgreSQL (not SQLite) for production
5. Enable rate limiting at the load balancer level
6. Regularly update dependencies
