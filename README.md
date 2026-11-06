# Bob2

Bob2 replaces Bobarr with Seerr for discovery and requests, Sonarr/Radarr for TV
and films/imports, Prowlarr for indexers, and Transmission sharing Gluetun's
NordVPN network. Existing Plex provides playback and is managed separately.
The target is **native TerraMaster TOS with Docker Compose**.

**Deployment templates are UNVALIDATED on the actual TOS version.** The local bundle is prepared for the two pilot libraries on TNAS. Folder creation,
permissions and existing Plex setup have been checked; no containers, image pulls
or deployment have been performed.

Seerr uses persisted SQLite; Redis has no established need and is omitted.
Rufus is no longer the intended coordinator. OpenClaw on TOS is an independent
investigation, with no dependency here. Bob2 requires neither compute host
(`hp`/`hp.lan`, `dell`/`dell.lan`).

- [Bob2 home page](portal/index.html): links to all apps; served on port 8088 by the portal service.
- [Interactive preparation script](scripts/deploy.py): downloads from GitHub and prompts for the destination and settings; TOS handles startup.
- [TerraMaster deployment bundle](docs/deploy-terramaster.md): files, required values and pilot setup.
- [Design and upstream sources](docs/design.md): dependencies, paths, permissions,
  VPN boundary, startup, updates, backups and Plex integration.
- [Staged implementation and acceptance](docs/acceptance.md): inventory gates,
  failure tests, integration and recovery criteria.
- [Continuation](TASK-CONTINUATION-BOB2.md): requirements, verified state and next action.
- [Compose](compose.yaml), [environment example](.env.example), and
  [Transmission resolver example](config/transmission-resolv.conf.example):
  intentionally require verified private values; do not start unchanged.

Local static checks: `python3 scripts/check-static.py` (requires PyYAML).
These inspect template invariants only. Docker CLI is unavailable locally, so
Compose CLI parsing, image health probes, TOS compatibility and runtime acceptance
remain outstanding. Do not substitute these checks for the pilot acceptance plan.

Adapted only from the media preparation in the read-only homelab-server-builds
repository; no Git history, credentials or unrelated infrastructure was copied.
