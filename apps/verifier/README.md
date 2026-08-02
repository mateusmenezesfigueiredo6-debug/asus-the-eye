# Verifier

Offline verification is available via `python3 -m asus_theye.cli audit-verify INPUT`.
`app.py` fixes the intended endpoint surface without starting or deploying a service.
Production reads require tenant-scoped authentication; `/health` exposes no tenant data
and `/metrics` contains only bounded aggregates.
