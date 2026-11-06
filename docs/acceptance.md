# Staged implementation and acceptance

**UNVALIDATED on actual TOS version — updated 6 November 2026.** Local bundle
preparation and the requested folder/Plex checks are authorised; pilot folders
have been created. No commands below authorise additional NAS access or changes.
Record later evidence with date, exact versions/digests, expected/observed result
and pass/fail; redact tokens, public addresses where private, and credentials.
Stop at a failed gate. Never fix a failure by bypassing VPN protection.

## 1. Local preparation (current scope)

Read design.md and continuation. Keep unverified env values blank; retain the two agreed pilot library paths. Run static
checks and review Git exclusions. Do not pull images or use containers to validate.
No staging, commit, push or remote creation is currently authorised.

## 2. Deployment prerequisites (later explicit authorisation)

Current authorisation is local bundle preparation plus the previously requested
folder/Plex checks. The user explicitly excluded TRAID and Docker/Compose inventory;
do not perform these checks on the NAS without new authorisation. The requirements
below describe unverified deployment prerequisites, not an instruction to inventory.


Obtain confirmation the four-disk TRAID synchronisation completed and is healthy;
70% was the last report. Record actual TOS, Docker Manager, Engine and Compose
versions, CPU architecture, TUN device, NET_ADMIN, firewall and IPv6/sysctl support.
Confirm approved native absolute paths, filesystem boundaries and free space,
CONFIG_ROOT/download/library separation, numerical IDs/groups and TOS ACL behaviour.
Inventory existing Plex URL, deployment, library paths, read permissions and backup.
No historical Proxmox path is a valid default. No formatting or storage conversion.

Choose reviewed compatible image tags/digests and resolver support. Decide trusted
NAS bind IPv4 and unused ports, reachable client subnets/access policy, timezone,
NordVPN OpenVPN service credentials and country/server policy, Transmission RPC
credentials, media group and Seerr ownership. OpenVPN is the draft protocol;
WireGuard needs a separate reviewed configuration. Indexers, quality profiles,
request approval/users, lawful test content, seeding limits, space thresholds,
backup encryption/location/retention and external access remain decisions.
No workers, OpenClaw, Rufus or Plex migration belong to this pilot.

## 3. Parser and configuration preflight

Create private `.env` only with verified values and restrictive permissions;
quote values according to Compose env syntax (not shell syntax), including dollar
signs. Never source the file in a shell or log rendered secrets. Copy resolver
example to the absolute private TRANSMISSION_RESOLV_FILE path. Pre-create approved
config folders for six services and complete/incomplete under DOWNLOAD_ROOT.
Use the existing bobFilms/bobTV directories as the final library roots. These directory operations require pilot authorisation.
Keep private data outside the checkout where possible; protect app-generated keys.

Use the actual target Compose parser: `docker compose --env-file .env -f compose.yaml config --quiet`.
Check long binds/create_host_path=false, dependency health/restart support, sysctls,
read-only resolver-file bind, port conflicts, non-overlapping config/data roots,
and image architecture. Parser success alone proves neither filesystem validity
nor runtime security. Do not remove unsupported safety fields to force a start.

## 4. Isolated VPN/downloader pilot

Start only reviewed Gluetun/Transmission on approved scratch state. Confirm the
selected Gluetun image supplies its healthcheck and resolver. Check effective
Transmission resolver file, routes and firewall; confirm RPC requires credentials
and is available to managers through gluetun:9091, with no NAS RPC/peer port.
Verify IPv4 egress matches VPN; attempt IPv6 and verify it is blocked. Generate
unique DNS queries from the downloader and observe uplink/tunnel traffic: no
queries to NAS/LAN/ISP resolver, Docker DNS forwarding or plaintext external DNS
outside the tunnel. Distinguish necessary VPN bootstrap/control traffic from
Transmission DNS and tracker/peer traffic. Use harmless traffic and approved test
endpoints; no untrusted diagnostic containers or downloads.

For each case below, observe continuous downloader IPv4/IPv6/DNS attempts, not just
a single IP check. Expected result is no non-VPN egress during failure; recovery
must restore VPN before transfers resume:

| Case | Required evidence |
|---|---|
| Cold start / invalid VPN credentials | Downloader gated or blocked; no direct Internet |
| Tunnel interruption / reconnect | Firewall continues blocking while health changes |
| Gluetun stop / crash / restart | No bypass; downloader safely recovers or stays stopped |
| Gluetun recreation / upgrade | Recreate downloader to join new namespace; recheck isolation |
| Transmission process/container restart | Resolver, routing and auth persist |
| Docker daemon restart / authorised NAS reboot | No startup race or IPv6/DNS leak; state persists |

Do not disable host networking/firewalls or disrupt production LAN to simulate
failure. Use isolated pilot scope. Health readiness and restart policies are not
kill switches. Any leak blocks acceptance; stop downloads and diagnose locally
within the later authorised scope. Keep seeding disabled until isolation passes.

## 5. App and Plex integration

Configure application authentication before exposing UIs to clients. Follow the
integration table in design.md for API keys, manager roots, indexer sync,
Transmission RPC and distinct TV/movie categories. Confirm Transmission stores
completed/incomplete paths as specified and disables UPnP/NAT-PMP port mapping.
LSIO requires settings changes while Transmission is stopped where documented;
never replace generated configuration blindly. Validate category behaviour in
the selected releases instead of assuming Transmission implements labels exactly
like another downloader.

Request one permitted film and TV item. Verify approval, monitoring, queue,
completion, import/rename, seeding retention, duplicate request handling, failure
and retry, free-space reporting and manager visibility of downloader paths.
Use disposable files to verify same-filesystem hardlinks (matching device/inode
and link count) or explicitly accept copy space/performance. No recursive chmod,
chown or 0777 repairs. Confirm Plex can read final media with its existing layout,
scan succeeds, Seerr reports availability and real playback works. Plex remains
outside the download VPN; do not mount incomplete downloads into Plex.

## 6. Persistence, recovery and release gate

Recreate each service against scratch configuration; settings/history/resume state
must persist. Take consistent app backups with apps quiesced or supported backup
methods, including SQLite, Transmission torrents/resume, Gluetun state and private
secrets stored separately. Verify encrypted backup retention and restore in an
isolated configuration without connecting duplicate managers to production.
Confirm existing Plex backup separately; TRAID is not backup.

Record old digests before deliberate one-service updates. Pause submissions and
transfers; stop Transmission before Gluetun changes and re-establish its namespace.
Test upgrade and rollback with a matching pre-migration database backup; image-only
rollback may fail after database migrations. No unattended updater. Release only
after all acceptance evidence passes. Keep old media/state until accepted and
retain continuation until authorised runtime work is verified.
