# Bob2 continuation — 4 November 2026

## Authorised requirements
Create a standalone repository at /home/ian/Projects/Bob2; initialise local Git
only. No staging, commit, push, GitHub repository or copied Git history. Preserve
any existing files. homelab-server-builds is read-only reference; read AGENTS.md,
TASK-CONTINUATION-MEDIA-TOS.md, docs/media-tos.md, MediaStack/compose.yaml and
MediaStack/.env.example. Adapt only relevant design/templates; no infrastructure,
Rufus code or credentials. Use British English.

Architecture: Seerr discovery/requests; Sonarr TV and Radarr films/imports;
Prowlarr indexers; Transmission through Gluetun/NordVPN; existing Plex playback.
Native TerraMaster TOS Docker Compose only, no VM/Proxmox. Verify upstream
dependencies; no Redis without established need. Rufus is no longer coordinator.
OpenClaw on TOS is a separate investigation and never a Bob2 dependency. Compute
hosts are hp/hp.lan and dell/dell.lan; do not contact or modify workers.

TRAID four-disk synchronisation last reported 70%; completion unconfirmed.
Local repository work only: no NAS access/changes, infrastructure operations,
containers, pulls, deployment, storage operations or formatting. Unknown native
paths, addresses, credentials, IDs and VPN settings must remain parameters.
Mark all deployment templates UNVALIDATED on the actual TOS version.

Deliver concise README, Compose/config templates, design and staged acceptance
covering fail-closed VPN, DNS/IPv6 leakage, persistence, consistent paths,
permissions, startup/health, updates/backups and Plex; exclusions for secrets,
private config and runtime data; this complete continuation. Report local checks,
Git status, exact files and prerequisites for a separately authorised TOS pilot.

## Verified progress and state
Bob2 did not exist before this task; no existing Bob2 files were replaced.
Read all five required reference files. SHA-256 comparison after preparation
confirmed those files unchanged. No reference Git state was changed by this task.
Only the relevant media design and templates were adapted; no history, secrets,
Rufus code or unrelated infrastructure copied.

Created README.md, compose.yaml, .env.example, .gitignore,
config/transmission-resolv.conf.example, docs/design.md, docs/acceptance.md,
scripts/check-static.py and this continuation file.

Official upstream documentation reviewed on 4 November 2026: Seerr Docker/database,
LSIO Sonarr/Radarr/Prowlarr/Transmission, Gluetun NordVPN/shared networking/DNS/
firewall, Docker networking and Compose startup order (links in design.md).
SQLite default establishes no Redis requirement. Corrected the reference draft's
unsupported `dns` option with shared container networking: use explicit read-only
resolver-file template. Added defensive shared-namespace/bridge IPv6 settings.
Resolver mounting, sysctls and selected image behaviour still require TOS testing.

Local Git initialised on main with no commits, staged files or remotes. All nine
project files are untracked. No GitHub repository, commit or push. No NAS/worker
access, pulls, container execution, deployment or storage operations performed.

## Checks performed
`python3 scripts/check-static.py` passed: YAML parse, six services, downloader VPN
namespace/no direct ports/networks/DNS override, firewall, IPv6 settings, required
blank env variables, non-creating bind mounts, private resolver mount, exclusion
rules, local Markdown links and whitespace. PyYAML 6.0.3 is installed locally.
Five reference file hashes unchanged. Docker CLI is absent: no Compose CLI parse,
image/tool/endpoint verification, TOS compatibility or runtime acceptance claimed.
`git status --short` shows only the intended untracked files/directories;
`git remote -v` is empty. These checks are static only.

## Outstanding decisions and ordered next steps
The local preparation task is complete. Keep this file for later runtime work.
1. Obtain a later explicit instruction authorising inventory/pilot scope; confirm
   four-disk TRAID completion/health before NAS operations.
2. Record actual TOS/Engine/Compose/CPU, TUN/firewall/sysctl capabilities, native
   paths/filesystems, ACLs/IDs, bind address/ports and existing Plex layout/backup.
3. Choose image digests, NordVPN OpenVPN service credentials/country policy,
   resolver file path, request/access policy, indexers/quality, seeding/space limits,
   lawful test items, backup destination/encryption/retention and external access.
   Do not put private values into this file or infer historical Proxmox values.
4. Follow docs/acceptance.md stages 3–6: actual parser preflight, isolated VPN/
   DNS/IPv6 failure matrix, app import/path/permission tests, existing Plex playback,
   then persistence, consistent backup/restore and update rollback. Stop on leaks.
5. Record redacted evidence and update validation status only for observed results.
   Git publication remains unauthorised unless requested separately.

## Exact next action
Review docs/acceptance.md stage 2 with the user and obtain a separately authorised
inventory/pilot scope plus confirmation of TRAID completion. Until then, perform
local review only; do not contact NAS/workers, deploy or run/pull containers.

## Resumed — 5 November 2026
User explicitly authorised read-only TNAS inventory after clarification that this
checks TOS/Docker, storage health, paths, permissions and existing Plex before
deployment. This supersedes the earlier prohibition on NAS contact for inventory
only. No deployment, pulls, containers, NAS changes or worker access authorised.
TRAID completion/health remains unconfirmed; check storage status first. Historical
Proxmox addresses/accounts are not verified native TOS connection details.
Local static checks passed on resumption; no staging, commits, remotes or pushes.
Exact next action: establish current TNAS hostname and SSH account/access, then
perform bounded read-only storage/OS/Docker/path/Plex inventory, without printing
credentials or private container environment. Stop before pilot mutations.

## Resumed — 6 November 2026
User requested inspection of `/Volume1/SHARED/Music` and
`/Volume1/SHARED/Movies` on `tnas`; both exist and contain media. Movies includes
`TV_Series` and multiple film/category directories. Parent directories show
`ian:ian`, mode 755 and additional ACLs; ACL contents were not inspected.
User then chose new folders under Movies for incoming media until satisfied
with Bob2. Created and verified `/Volume1/SHARED/Movies/bobFilms` and
`/Volume1/SHARED/Movies/bobTV`; both show `ian:ian`, mode 755 and additional ACLs.
No existing media moved, permissions changed or applications deployed/configured.
Use these as the pilot film/TV destinations; leave existing libraries in place.
Compose/container roots still require adaptation before deployment. Download
location, app IDs/ACL access, storage health and remaining inventory are unverified.
Local-only Git restriction remains; folder creation does not authorise deployment.

## Local deployment bundle — 6 November 2026
User explicitly narrowed NAS checks to folder permissions and Plex setup; do not
perform TRAID or Docker/Compose inventory. Folder access was checked as plex:
both pilot roots allow read/traverse but not write. Numeric owner/group are 0:0,
displayed as ian:ian, mode 755; getfacl reports basic rwx/r-x/r-x entries.
Plex runs natively from Volume2 as UID 10001/GID 10002, with library database and
config under `/Volume2/Plex/Library/Application Support/Plex Media Server`.
Its existing libraries use individual native directories; neither pilot folder
was registered at inspection. CLI library creation instructions were supplied;
execution is unconfirmed. No Plex configuration was changed by this agent.

User authorised local TerraMaster deployment bundle preparation. Compose now uses
FILMS_ROOT/TV_ROOT (set to the chosen paths in .env.example) and DOWNLOAD_ROOT.
Sonarr mounts only downloads and bobTV; Radarr only downloads and bobFilms;
Transmission only downloads, its config and the private resolver. Separate mounts
prioritise limited access; copy imports/extra space are expected, not hardlinks.
Added docs/deploy-terramaster.md with private-file setup, remaining values,
deployment commands and app settings. Updated design/acceptance/README and static
checks. No NAS operations, deployment, image pulls, staging, commits or pushes
performed during bundle preparation. Configuration/download locations, non-root
app IDs and write grants, image versions, bind address/ports and credentials still
require user input. Do not infer these from the root SSH account or Plex account.
Next: supply those inputs and prepare private deployment files; target parser and
runtime VPN/application acceptance remain unverified.

## Interactive preparation wizard — 6 November 2026
User requested a deployer that starts by asking for bundle/destination, extracts
the bundle, prompts for all settings and prepares configuration/directories.
User clarified that startup is handled by TOS. Implemented scripts/deploy.py with
Python standard library only; no Docker commands or container startup. Run as
root locally on TNAS. It validates archive paths/types, rejects symlink traversal
and existing-file collisions, prompts for every env value, hides credentials,
confirms passwords, writes private literal-quoted .env and a group-readable
resolver file, and creates app-owned directories. Existing ownership/modes are
preserved; a prompted non-recursive setfacl grant is available only for specific
media directories lacking write access. Supplied bind ports are checked by local
socket bind, without listening. No TRAID/Docker/Plex inventory is performed.
TOS is responsible for importing the Compose/env files, validation and startup.
Application UI integrations and runtime VPN tests remain separate steps.

Existing /Volume2/Bob2 extraction reported by user is not overwritten: use a fresh
destination with the updated archive, e.g. /Volume2/Bob2-pilot. Configuration is
retained after interruption/failure; restarting the wizard requires a fresh
destination. No remote script execution, deployment or permissions changes were
performed during implementation. Seven offline tests passed (including malicious
archive rejection, private file permissions, existing directory preservation and
a full mocked setup with no subprocess/Docker calls); static checks also passed.
Updated README/deployment guide and rebuilt /tmp/Bob2-terramaster.tar.gz including
the wizard. Still no commits, staging, remotes or pushes.

## Git publication and GitHub download — 6 November 2026
User explicitly authorised committing/pushing Bob2, superseding the earlier
local-only/no-commit restriction. No remote existed and emmjam/Bob2 did not exist;
create a private GitHub repository under the authenticated emmjam account.
Deployer now prompts for GitHub owner/repository, ref and destination, downloads
the repository tarball through the GitHub API and safely strips its wrapper.
Private access uses GH_TOKEN/GITHUB_TOKEN or a hidden token prompt; no token is
stored in project files, commands or configs. Redirects are HTTPS GitHub-only and
drop the Authorization header. TOS still owns startup; no Docker calls are made.
Nine offline tests and static checks passed. Push/remote verification is reported
separately in the final response; no NAS deployment is implied by publication.
