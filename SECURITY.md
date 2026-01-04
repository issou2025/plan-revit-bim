# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it by emailing entreprise2rc@gmail.com. Please do not create a public GitHub issue for security vulnerabilities.

## Security Best Practices

### Production Deployment

When deploying this application to production, please ensure you:

1. **Change Default Credentials**
   - Update `ADMIN_USER` and `ADMIN_PASS` environment variables
   - Use strong, unique passwords
   - Never commit credentials to version control

2. **Update Secret Keys**
   - Change `SECRET_KEY` to a cryptographically secure random string
   - Change `ADMIN_SECRET_URL` to a unique, hard-to-guess path
   - Store these values in environment variables or a secure secrets manager

3. **Use HTTPS**
   - Always use HTTPS in production
   - Enable HSTS (HTTP Strict Transport Security)
   - Consider using a reverse proxy like nginx or Apache

4. **File Upload Security**
   - The application validates file extensions, but consider additional validation
   - Set appropriate file size limits
   - Store uploaded files outside the web root if possible
   - Scan uploaded files for malware

5. **Database Security**
   - This application uses JSON files for storage
   - Ensure proper file permissions on the `uploads/` directory
   - Consider using a proper database for production
   - Implement regular backups

6. **Session Security**
   - Set `SESSION_COOKIE_SECURE=True` when using HTTPS
   - Set `SESSION_COOKIE_HTTPONLY=True`
   - Set `SESSION_COOKIE_SAMESITE='Lax'` or `'Strict'`

7. **Rate Limiting**
   - Implement rate limiting on the contact form
   - Implement rate limiting on admin login attempts
   - Consider using Flask-Limiter

8. **Input Validation**
   - All user inputs are sanitized by Flask/Jinja2
   - Review file upload handling for your use case
   - Validate and sanitize all form inputs

9. **Logging and Monitoring**
   - Monitor application logs for suspicious activity
   - Set up alerts for failed login attempts
   - Review traffic logs regularly

10. **Updates**
    - Keep Flask and all dependencies up to date
    - Regularly check for security advisories
    - Run `pip list --outdated` to check for updates

## Environment Variables

Create a `.env` file (never commit this!) with production values:

```bash
SECRET_KEY=<generate-strong-random-key>
ADMIN_USER=<your-admin-email>
ADMIN_PASS=<strong-password>
ADMIN_SECRET_URL=<unique-hard-to-guess-path>
DEBUG=False
```

To generate a secure secret key in Python:
```python
import secrets
print(secrets.token_hex(32))
```

## Security Checklist for Production

- [ ] Changed default admin credentials
- [ ] Changed SECRET_KEY to random value
- [ ] Changed ADMIN_SECRET_URL to unique value
- [ ] Disabled DEBUG mode (DEBUG=False)
- [ ] Using HTTPS
- [ ] Set secure cookie flags
- [ ] Implemented rate limiting
- [ ] Set up regular backups
- [ ] Configured proper file permissions
- [ ] Set up monitoring and alerts
- [ ] Reviewed and updated all dependencies

## Contact

For security concerns, contact: entreprise2rc@gmail.com
