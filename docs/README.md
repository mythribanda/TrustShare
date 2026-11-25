# TrustShare – Documentation

Start with the [project README](../README.md) for an overview, then use this index.
The live system: `https://<YOUR-DOMAIN>`

## Using and running TrustShare

| Document | What it covers |
|---|---|
| [User guide](USER_GUIDE.md) | Step-by-step guide for regular users |
| [Admin guide](ADMIN_GUIDE.md) | Step-by-step guide for administrators (user management, audit logs, security monitoring, reports) |
| [Setup and configuration](setup.md) | Running with Docker, local HTTPS, Azure Blob Storage or AWS S3, creating the first admin and demo data, environment variables, tests, Postman, troubleshooting |
| [Features](features.md) | The complete feature list, grouped by area |
| [Security test report](SECURITY_TEST_REPORT.md) | Milestone 4 security test report (SAST, dependency audits, manual defensive checks) |
| [Security testing (live checklist)](security-testing.md) | Live-deployment OWASP Top 10 security checklist template (`TODO: fill from my own run`) |
| [Performance](performance.md) | Performance & responsiveness template (`TODO: fill from my own run`) |
| [Deployment guide](../DEPLOYMENT.md) | Production setup and step-by-step deployment with HTTPS, operations, backups, troubleshooting |
| [API reference](api.md) | Every endpoint by module, with the permission it needs |

## Design

| Document | What it covers |
|---|---|
| [Requirements](requirements.md) | Problem and objective, roles, permission matrix, functional and non-functional requirements, user stories |
| [Architecture](architecture.md) | System overview, backend layers, request flows, security design, milestone additions |
| [Database design](database.md) | PostgreSQL tables, MongoDB collections, Redis keys, object storage |
| [Encryption and key management](key-management.md) | Envelope encryption, algorithms, key lifecycle (creation, rotation, recovery, deletion), the secure vault |
| [Wireframes](wireframes.html) | The UI plan made before building (open the file in a browser) |
| [AWS IAM policy](aws-iam-policy.json) | Least-privilege policy for using real AWS S3 |

## Evaluation

| Document | What it covers |
|---|---|
| [Project brief coverage](brief-coverage.md) | Every item of the project brief → where it is implemented and how it is tested, plus what was done differently and what is out of scope |
| [Reference screenshots](screenshots/reference/) | Upstream placeholder screenshots (`docs/screenshots/reference/`) — **Note:** these are placeholders from the reference repository and will be replaced with screenshots from my own deployment |
| [Milestone 3 screenshots](screenshots/m3/) | Milestone 3 module screenshots |
| [Test results](test-results/) | Recorded Milestone 4 security testing outputs and defensive test suite |
| [Postman collections](../postman/) | API checks for Milestones 2 and 3 |
