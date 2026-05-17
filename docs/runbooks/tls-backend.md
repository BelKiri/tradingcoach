# Runbook: Backend TLS at the reverse proxy

This runbook describes how transport security for the backend API is
operated. Shape and procedure only — no hostnames, network addresses,
server paths, vendor product names, or certificate subjects.

## Purpose

The backend serves plain HTTP on a loopback interface. A reverse proxy on
the same host terminates TLS for public clients. Clients never negotiate
TLS with the application process directly.

## Architecture

```
[ Client ] --TLS--> [ Reverse proxy :443 ]
                         |
                         v  plain HTTP, loopback
                   [ Application ]
```

- TLS ends at the reverse proxy; the app container is unchanged.
- Certificate: publicly trusted, domain-validated via HTTP on port 80.
- Renewal: automated on a host schedule; manual renew when automation fails.

## Preconditions

1. API hostname resolves in public DNS to the host’s public address.
2. Port 80 reachable from the internet (validation and, until redirect,
   plain HTTP).
3. Port 443 open in the host firewall for the proxy after certificates exist.
4. Dated proxy site config backed up outside the live config directories.

## Initial enablement (sequence)

Exact commands: private operations runbook.

1. Backup current proxy site config to a dated archive.
2. Install the host OS certificate automation client (one client only).
3. Issue a certificate for the API hostname via HTTP validation while port 80
   still serves plain HTTP.
4. Update proxy config: listen on 443 with issued cert/key; TLS 1.2 minimum;
   current cipher policy; HSTS max-age one year **without** preload; keep
   port 80 proxying (no redirect) until callers are verified on HTTPS.
5. Test config syntax, reload proxy, confirm HTTPS health externally.
6. Set the frontend deployment backend base URL to the HTTPS origin;
   redeploy and verify flows.
7. Enable HTTP→HTTPS redirect for the API hostname on port 80 only; leave
   the numeric-address listener on port 80 as plain HTTP for rollback.
8. Confirm automated renewal with a successful dry-run.

## Checking certificate validity

| Check | Operationally |
|-------|----------------|
| Trusted chain | HTTPS health request in a validating client; no warnings. |
| Identity | Presented name matches the API hostname you expect. |
| Expiry | Note client-displayed expiry; renew well before (e.g. 30 days). |
| HTTPS up | Health path returns success over HTTPS. |
| HTTP policy | After redirect: hostname on port 80 → redirect; numeric address on port 80 → success without redirect. |

Review the renewal service logs on the host after any failed run (paths in
private runbook).

## Force renewal

When automation fails, expiry is near, or keys were rotated intentionally:

1. Port 80 reachable; proxy serves the HTTP validation path for the API hostname.
2. Run the client **renew** for that certificate name only.
3. Use **force** / re-issue mode if supported and expiry is not yet due.
4. Reload the proxy after success.
5. Repeat external checks above; log reason and time.

## Auto-renewal failure recovery

**Symptoms:** scheduled job failure; expiry within 30 days; trust errors in clients.

1. Read renewal service logs for the latest run.
2. Fix root cause: DNS drift, firewall on 80, proxy blocking validation path,
   clock skew, CA rate limits.
3. Dry-run renewal; live renew only after dry-run succeeds.
4. Reload proxy if new cert material was written.
5. Verify externally; if still failing, force renewal.
6. Before expiry: revert frontend backend URL to prior HTTP origin and use
   plain HTTP on the numeric address while debugging (private rollback).

## Rollback

| When | Action |
|------|--------|
| Before frontend URL change | Restore dated proxy backup; reload. Numeric HTTP still works. |
| After frontend URL change | Revert frontend backend URL; redeploy; restore proxy backup if needed. |
| After hostname redirect | Restore pre-redirect backup; reload. |

Edit the source site file, not only the enabled symlink.

## Boundaries

- No extra public paths beyond existing API routes and health.
- No third-party DNS “proxy” mode if design is DNS-only to the host.
- No HSTS preload without a separate decision.
- No host-specific secrets in this document.

## Related

Host commands, paths, backups, DNS posture, and env values:
`.private/runbooks/` (private).
