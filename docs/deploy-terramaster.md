# TerraMaster pilot bundle

Prepared locally on 6 November 2026; not deployed or runtime validated on TOS.
This bundle uses native TOS Compose and the existing native Plex installation.
No NAS inventory beyond the authorised folder permissions/Plex checks was done.

## Interactive preparation script (recommended)

Copy `scripts/deploy.py` from the GitHub repository `emmjam/Bob2` to TNAS.
The script downloads the bundle directly from GitHub; no separate archive copy is needed.
Run the script using Python 3 as root; no extra Python packages are needed:

```bash
python3 /path/to/deploy.py
```

It downloads directly from `emmjam/Bob2`, branch `main`, without repository or
branch prompts. It asks only for the deployment destination before download.
The destination is emptied first, preserving only the deploy script.
This deletes previous `.env`, resolver files and appdata inside the destination.
Use a dedicated Bob2 directory; media/downloads outside it are untouched.
The downloaded archive is temporary and removed automatically. Private repositories
require a GitHub token with Contents read access: supply GH_TOKEN/GITHUB_TOKEN in
the process environment or use the hidden prompt after an access-denied response.
The script never saves the token. A 404 can also mean the repository/ref is wrong.

The script fills image references and Plex account IDs automatically and prompts for the remaining settings, with the agreed film/TV paths and
suggested directory, timezone and port defaults. All six images are hard-coded to `latest`; there are no image prompts. The script does not pull images. Credentials
are hidden and passwords confirmed. It writes a private mode-600 `.env`, creates
the resolver file, and prepares the service/download directories. New service
config directories are private to their app accounts. Existing directories are
never recursively chowned or chmodded. If the chosen media account cannot write
to existing pilot folders, it sets Plex ownership (10001:10002) on those exact directory entries and
rechecks access. It does not recurse or change parent directories; POSIX named-user
ACL grants were insufficient on the observed TOS share.

The script checks the supplied ports by briefly binding them without listening;
it does not inspect storage, Docker or Plex, or change Plex libraries. It never
runs Docker, starts containers or deploys the project. **TOS handles startup.**
Configuration files/directories already created remain on failure or cancellation;
no rollback occurs after the initial destination cleanup. Restarting the wizard clears the destination again; existing external media/download
directories are preserved.

Use the current repository version with this script. Older DATA_ROOT-based bundles
are rejected. Secrets containing backslashes are rejected rather than relying on
parser-specific escaping. Dollar signs, spaces, hash marks and quotes are preserved
using Compose literal single-quoted values. Do not source `.env` as a shell script.

## Manual preparation alternative

In an already extracted project directory:

```bash
umask 077
cp -n .env.example .env
cp -n config/transmission-resolv.conf.example config/transmission-resolv.conf
```

Fill `.env` as described below and prepare directories/permissions yourself.

## Values to supply

| Variable | Value or decision |
|---|---|
| FILMS_ROOT | Already set: `/Volume1/SHARED/Movies/bobFilms` |
| TV_ROOT | Already set: `/Volume1/SHARED/Movies/bobTV` |
| DOWNLOAD_ROOT | Defaults to `/Volume1/SHARED/Movies/bobDownloads`; created by the preparation script if missing |
| CONFIG_ROOT | Choose a private, persistent absolute directory outside downloads/libraries; not selected yet |
| TRANSMISSION_RESOLV_FILE | Absolute filename of the private resolver copy above |
| MEDIA_UID / MEDIA_GID | Automatically uses the existing Plex account: UID `10001`, GID `10002`; no prompts or new user |
| SEERR_UID / SEERR_GID | Automatically uses the same Plex UID `10001`, GID `10002`; no prompts |
| TZ | `Europe/London` is the intended timezone |
| NAS_BIND_IP | Automatically set to `192.168.0.102`; no prompt |
| SONARR_PORT / RADARR_PORT / PROWLARR_PORT / SEERR_PORT | Uses `8989` / `7878` / `9696` / `5055` automatically; prompts for an alternative only when unavailable |
| NORDVPN_SERVICE_USER / NORDVPN_SERVICE_PASSWORD | Read automatically from `/home/ian/.nordvpn` on TNAS; no credential prompts |
| NORDVPN_COUNTRIES | Automatically set to `Netherlands`; no prompt |
| TRANSMISSION_USER / TRANSMISSION_PASSWORD | Choose private downloader RPC credentials |
| All six *_IMAGE variables | Automatically set to `latest` from the repositories listed in `.env.example`; no prompts |

Create config subdirectories named gluetun, transmission, sonarr, radarr,
prowlarr and seerr under CONFIG_ROOT, plus complete and incomplete under
DOWNLOAD_ROOT, only after choosing and authorising those locations. Set ownership
per service; do not use root app IDs or recursive permission changes to existing
media as a shortcut. Gluetun config permissions must match its selected image.

Verified folder permissions are currently UID/GID 0:0, mode 755. The `plex` account
(10001:10002) can read/traverse both pilot folders but cannot write. Bob2's media
account needs explicitly granted write access; it is not configured yet. Preserve
Plex read/traverse access to imported files and their subdirectories.

## Deploy through TOS

When preparation completes, create/import a Compose project in TOS using the
printed destination and `compose.yaml`. Ensure TOS loads the generated `.env`;
if its UI requires explicit project environment settings, supply the values there
privately. Do not paste credentials into chat or public logs. Exact TOS UI behaviour
and compatibility remain unverified. Do not remove the shared VPN namespace,
firewall or bind-safety settings to work around an import failure.

TOS validates and starts the project. Before submitting downloads, complete the
VPN/DNS/IPv6 checks in [acceptance.md](acceptance.md); healthy status alone does
not prove isolation. No Transmission ports are published on the NAS. This script
does not configure application integrations or prove runtime readiness.

## Application setup

| Application | Setting |
|---|---|
| Sonarr | Root `/data/media/tv` → native bobTV folder |
| Radarr | Root `/data/media/movies` → native bobFilms folder |
| Transmission | Complete `/data/downloads/complete`; incomplete `/data/downloads/incomplete` |
| Sonarr/Radarr downloader | Host `gluetun`, port `9091`, chosen RPC credentials; no SSL on this private bridge |
| Prowlarr | Sonarr `http://sonarr:8989`; Radarr `http://radarr:7878`; supply their API keys |
| Seerr | Sonarr/Radarr URLs above; their API keys, pilot roots, quality/request policy and existing Plex connection |
| Plex | Separate film library bobFilms and TV library bobTV, using their native absolute paths |

Enable application authentication before normal use. Downloads have identical
container paths in both managers and Transmission. Verify TV/film categorisation
with the selected Transmission release. Plan for copy imports and space for both
downloads and imported media: the restricted separate mounts do not promise hardlinks.

Plex library creation commands were supplied earlier; execution is unconfirmed.
Do not duplicate an existing library. Test one permitted film and TV episode,
including import and Plex playback. Existing libraries remain untouched until the
user accepts Bob2. Nothing in this bundle changes Plex configuration automatically.

NordVPN credentials are loaded before destination cleanup from
`/home/ian/.nordvpn` on TNAS, never from Git. Supported formats are
`USERNAME=...` / `PASSWORD=...` assignments (optionally quoted), or an OpenVPN
credentials file with username on line one and password on line two. Values are
not executed or printed. Missing/invalid files stop preparation before cleanup.
