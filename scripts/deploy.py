#!/usr/bin/env python3
"""Interactive TNAS installer. Standard library only; run locally on TNAS as root."""
import getpass
import ipaddress
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import socket
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.parse
import urllib.request


SERVICES = ('gluetun', 'transmission', 'sonarr', 'radarr', 'prowlarr', 'seerr')
REPOS = {
    'GLUETUN_IMAGE': 'qmcgaw/gluetun',
    'TRANSMISSION_IMAGE': 'lscr.io/linuxserver/transmission',
    'SONARR_IMAGE': 'lscr.io/linuxserver/sonarr',
    'RADARR_IMAGE': 'lscr.io/linuxserver/radarr',
    'PROWLARR_IMAGE': 'lscr.io/linuxserver/prowlarr',
    'SEERR_IMAGE': 'ghcr.io/seerr-team/seerr',
}


def ask(label, default='', secret=False, validate=None):
    while True:
        prompt = label + (f' [{default}]' if default and not secret else '') + ': '
        value = (getpass.getpass(prompt) if secret else input(prompt))
        if not value:
            value = default
        if not value or any(c in value for c in '\r\n\x00'):
            print('A non-empty, single-line value is required.')
            continue
        try:
            if validate:
                validate(value)
        except (ValueError, OSError) as error:
            print(error)
            continue
        return value


def yes(label):
    return input(label + ' [y/N]: ').strip().lower() in ('y', 'yes')


def absolute(value):
    p = Path(value)
    if not p.is_absolute() or '..' in p.parts:
        raise ValueError('Use an absolute path without .. components.')
    for part in (p, *p.parents):
        if part.is_symlink():
            raise ValueError(f'Symlinks are not allowed in deployment paths: {part}')
    if p == Path('/'):
        raise ValueError('The filesystem root is not a deployment directory.')
    return p


def mkdirs(path):
    """Create traversable parents without modifying any existing directory."""
    missing = []
    current = path
    while not current.exists():
        missing.append(current)
        current = current.parent
    for folder in reversed(missing):
        folder.mkdir(mode=0o755)
        folder.chmod(0o755)


class GitHubRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urllib.parse.urlparse(newurl)
        if parsed.scheme != 'https' or parsed.hostname not in ('api.github.com', 'codeload.github.com', 'github.com'):
            raise ValueError('Refusing an unexpected GitHub archive redirect.')
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        redirected.remove_header('Authorization')
        return redirected


def repository(value):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', value):
        raise ValueError('Enter GitHub owner/repository, for example emmjam/Bob2.')


def download_bundle(repo, ref, destination):
    repository(repo)
    url = f'https://api.github.com/repos/{repo}/tarball/{urllib.parse.quote(ref, safe="")}'
    token = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
    opener = urllib.request.build_opener(GitHubRedirect())
    for attempt in range(2):
        headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'Bob2-preparer'}
        if token:
            headers['Authorization'] = 'Bearer ' + token
        try:
            with opener.open(urllib.request.Request(url, headers=headers), timeout=60) as response:
                with destination.open('wb') as output:
                    total = 0
                    while True:
                        data = response.read(65536)
                        if not data:
                            break
                        total += len(data)
                        if total > 20 * 1024 * 1024:
                            raise ValueError('GitHub archive exceeds 20 MiB.')
                        output.write(data)
            return
        except urllib.error.HTTPError as error:
            if error.code in (401, 403, 404) and attempt == 0:
                print('GitHub access denied or repository/ref not found. For a private repo, supply a token with repository Contents read access.')
                token = getpass.getpass('GitHub token (hidden, not saved): ')
                if not token:
                    raise ValueError('GitHub token required for retry.') from None
            else:
                raise ValueError(f'GitHub archive request failed (HTTP {error.code}); check repository/ref and token access.') from None
        except urllib.error.URLError:
            raise ValueError('Could not download from GitHub; check TNAS network/TLS access.') from None


def empty_destination(destination, script=None):
    destination = absolute(str(destination))
    protected = {Path('/Volume1/SHARED'), Path('/Volume1/SHARED/Movies'),
                 Path('/Volume1/SHARED/Music'), Path('/Volume1/SHARED/Movies/bobFilms'),
                 Path('/Volume1/SHARED/Movies/bobTV')}
    if len(destination.parts) < 3 or destination in protected or destination.is_mount():
        raise ValueError('Choose a dedicated project directory, not a volume or media folder.')
    if not destination.exists():
        mkdirs(destination)
        return set()
    if not destination.is_dir():
        raise ValueError('Destination must be a directory.')
    preserved = set()
    for candidate in (script or Path(__file__).resolve(), destination / 'deploy.py'):
        if candidate.is_file() and not candidate.is_symlink() and destination in candidate.parents:
            preserved.add(candidate)
    # Refuse nested mounts before deleting anything; never traverse symlink targets.
    for base, directories, _ in os.walk(destination, followlinks=False):
        for name in directories:
            path = Path(base) / name
            if not path.is_symlink() and path.is_mount():
                raise ValueError(f'Refusing to clear a destination containing a mount: {path}')

    def clear(folder):
        for child in folder.iterdir():
            if child in preserved:
                continue
            if child.is_symlink() or not child.is_dir():
                child.unlink()
            elif any(child in kept.parents for kept in preserved):
                clear(child)
            else:
                shutil.rmtree(child)
    clear(destination)
    return preserved


def extract(bundle, destination, github=False, preserved=()):
    """Validate entire archive before writing; reject links, devices and traversal."""
    destination = absolute(str(destination))
    allowed = {'compose.yaml', '.env.example', '.gitignore', 'README.md',
               'TASK-CONTINUATION-BOB2.md', 'config', 'docs', 'scripts', 'tests', 'portal'}
    with tarfile.open(bundle, 'r:gz') as archive:
        members = archive.getmembers()
        if github:
            roots = {PurePosixPath(m.name).parts[0] for m in members if PurePosixPath(m.name).parts}
            if len(roots) != 1 or roots.intersection({'.', '..', '/'}):
                raise ValueError('Unexpected GitHub archive layout.')
            root = next(iter(roots))
            normalised = []
            for member in members:
                original = PurePosixPath(member.name)
                if original.is_absolute() or '..' in original.parts:
                    raise ValueError('Unsafe GitHub archive path.')
                if member.name.rstrip('/') == root and member.isdir():
                    continue
                member.name = '/'.join(original.parts[1:])
                normalised.append(member)
            members = normalised
        seen = set()
        total = 0
        for member in members:
            path = PurePosixPath(member.name)
            if (path.is_absolute() or '..' in path.parts or not path.parts
                    or path.parts[0] not in allowed or '\\' in member.name
                    or not (member.isdir() or member.isfile())):
                raise ValueError(f'Unsafe/unexpected archive member: {member.name}')
            if path in seen:
                raise ValueError(f'Duplicate archive member: {path}')
            seen.add(path)
            total += member.size
            if total > 20 * 1024 * 1024:
                raise ValueError('Bundle exceeds the 20 MiB deployment-file limit.')
            target = destination.joinpath(*path.parts)
            absolute(str(target))
            if target in preserved and member.isfile():
                continue
            if target.exists() and not (target.is_dir() and member.isdir()):
                raise ValueError(f'Refusing to overwrite {target}; choose a new destination.')
        for required in ('compose.yaml', '.env.example', 'config/transmission-resolv.conf.example'):
            if not any(m.name == required and m.isfile() for m in members):
                raise ValueError(f'Bundle missing {required}')
        if (destination / '.env').exists():
            raise ValueError('Destination already has .env; choose a new destination.')
        mkdirs(destination)
        for member in members:
            target = destination / member.name
            if target in preserved:
                continue
            if member.isdir():
                mkdirs(target)
            else:
                mkdirs(target.parent)
                with archive.extractfile(member) as source, target.open('xb') as output:
                    shutil.copyfileobj(source, output)
                target.chmod(0o600)


def numeric(value):
    if not value.isdecimal() or int(value) < 1 or int(value) > 2147483647:
        raise ValueError('Enter a positive, non-root numeric UID/GID.')


def port(value):
    if not value.isdecimal() or not 1024 <= int(value) <= 65535:
        raise ValueError('Enter a port between 1024 and 65535.')


def ipv4(value):
    address = ipaddress.IPv4Address(value)
    if address.is_unspecified or address.is_multicast or address.is_loopback:
        raise ValueError('Use the NAS LAN IPv4 address, not a wildcard/loopback.')


def image(value):
    if not re.fullmatch(r'[A-Za-z0-9._/:@-]+', value):
        raise ValueError('Enter a valid full image reference without spaces.')
    if ':' not in value.rsplit('/', 1)[-1]:
        raise ValueError('Supply an image tag or digest.')


def dotenv(value):
    # Compose single quotes preserve literal $, # and spaces; escaped quotes allowed.
    # Reject backslashes rather than depending on ambiguous parser escape handling.
    if '\\' in value:
        raise ValueError('Backslashes in setting values are unsupported; choose a value without them.')
    return "'" + value.replace("'", "\\'") + "'"


def private_write(path, text):
    absolute(str(path))
    with path.open('x', encoding='utf-8') as output:
        os.chmod(path, 0o600)
        output.write(text)


def disjoint(paths):
    for i, first in enumerate(paths):
        for second in paths[i + 1:]:
            if first == second or first in second.parents or second in first.parents:
                raise ValueError(f'Paths must not overlap: {first}, {second}')


def prepare_owned(path, uid, gid, mode=0o2755):
    """Only create/chown a new directory; never alter an existing directory."""
    absolute(str(path))
    if path.exists():
        if not path.is_dir():
            raise ValueError(f'Not a directory: {path}')
        return
    mkdirs(path)
    os.chown(path, uid, gid)
    path.chmod(mode)  # media roots are traversable; service config stays private


def repair_media_owner(path, uid, gid):
    # TOS share ACLs may not honour a POSIX named-user grant. Own only the
    # selected directory entry; never recurse into media or alter parent folders.
    absolute(str(path))
    os.chown(path, uid, gid)
    if not access_as(path, uid, gid, os.R_OK | os.W_OK | os.X_OK):
        raise ValueError(f'Access still denied after setting Plex ownership: {path}. No deployment started.')


def access_as(path, uid, gid, flags):
    pid = os.fork()
    if pid == 0:
        try:
            # Docker mounts this directory directly; host ancestors are not
            # traversed by the app. Enter the mount source before dropping root.
            os.chdir(path)
            os.setgroups([])
            os.setgid(gid)
            os.setuid(uid)
            os._exit(0 if os.access('.', flags) else 1)
        except OSError:
            os._exit(1)
    return os.waitpid(pid, 0)[1] == 0


def nordvpn_credentials(path=Path('/home/ian/.nordvpn')):
    try:
        lines = [line.strip() for line in path.read_text().splitlines()
                 if line.strip() and not line.lstrip().startswith('#')]
    except OSError:
        raise ValueError(f'Cannot read NordVPN credentials from {path}. Place the credentials file there on TNAS.') from None
    aliases = {'USERNAME': 'NORDVPN_SERVICE_USER', 'USER': 'NORDVPN_SERVICE_USER',
               'PASSWORD': 'NORDVPN_SERVICE_PASSWORD', 'PASS': 'NORDVPN_SERVICE_PASSWORD',
               'OPENVPN_USER': 'NORDVPN_SERVICE_USER', 'OPENVPN_PASSWORD': 'NORDVPN_SERVICE_PASSWORD',
               'NORDVPN_SERVICE_USER': 'NORDVPN_SERVICE_USER',
               'NORDVPN_SERVICE_PASSWORD': 'NORDVPN_SERVICE_PASSWORD'}
    credentials = {}
    for line in lines:
        key, separator, value = (line[7:] if line.startswith('export ') else line).partition('=')
        if separator and key.strip() in aliases:
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                value = value[1:-1]
            credentials[aliases[key.strip()]] = value
    if not credentials and len(lines) == 2:
        credentials = dict(zip(('NORDVPN_SERVICE_USER', 'NORDVPN_SERVICE_PASSWORD'), lines))
    if set(credentials) != {'NORDVPN_SERVICE_USER', 'NORDVPN_SERVICE_PASSWORD'} or not all(credentials.values()):
        raise ValueError('NordVPN file must contain USERNAME/PASSWORD assignments or two lines: username then password.')
    for value in credentials.values():
        if any(c in value for c in '\r\n\x00'):
            raise ValueError('Invalid multiline NordVPN credentials.')
        dotenv(value)
    return credentials


def available_port(key, default, address, used_ports):
    value = default
    while True:
        if value not in used_ports:
            try:
                with socket.socket() as sock:
                    sock.bind((address, int(value)))
                used_ports.add(value)
                return value
            except OSError:
                pass
        print(f'{key}: port {value} unavailable on {address}.')
        value = ask(key + ' alternative port', validate=port)


def write_portal(folder, values):
    page = folder / 'index.html'
    text = page.read_text()
    for app, default in [('SONARR', '8989'), ('RADARR', '7878'),
                         ('PROWLARR', '9696'), ('SEERR', '5055')]:
        text = text.replace('192.168.0.102:' + default,
                            values['NAS_BIND_IP'] + ':' + values[app + '_PORT'])
    page.write_text(text)
    # nginx:alpine worker account; TOS ACLs require explicit ownership.
    os.chown(folder, 101, 101)
    os.chown(page, 101, 101)
    folder.chmod(0o755)
    page.chmod(0o644)


def main():
    os.umask(0o077)
    repo = 'emmjam/Bob2'
    ref = 'main'
    destination = Path(ask('Absolute deployment destination', '/home/ian/BOB2', validate=absolute))
    if os.geteuid() != 0:
        raise ValueError('Run this script as root on TNAS to prepare app-owned directories.')
    vpn_credentials = nordvpn_credentials()
    print(f'Clearing {destination}, preserving the deploy script only (including .env and appdata removal).')
    preserved = empty_destination(destination)
    with tempfile.TemporaryDirectory(prefix='bob2-download-') as temporary:
        bundle = Path(temporary) / 'bundle.tar.gz'
        print(f'Downloading {repo} at {ref} from GitHub...')
        download_bundle(repo, ref, bundle)
        extract(bundle, destination, github=True, preserved=preserved)
    print(f'Extracted to {destination}. Destination cleared; deploy script preserved.')
    print('Enter settings below. No NAS inventory or Plex changes will be performed.')
    values = {}
    template = (destination / '.env.example').read_text()
    keys = [line.split('=', 1)[0] for line in template.splitlines()
            if line and not line.startswith('#')]
    if set(keys) != set(REPOS) | {
        'CONFIG_ROOT', 'DOWNLOAD_ROOT', 'FILMS_ROOT', 'TV_ROOT', 'MEDIA_UID',
        'MEDIA_GID', 'SEERR_UID', 'SEERR_GID', 'TZ', 'NAS_BIND_IP', 'SEERR_PORT',
        'SONARR_PORT', 'RADARR_PORT', 'PROWLARR_PORT', 'PORTAL_PORT', 'NORDVPN_SERVICE_USER',
        'NORDVPN_SERVICE_PASSWORD', 'NORDVPN_COUNTRIES', 'TRANSMISSION_USER',
        'TRANSMISSION_PASSWORD', 'TRANSMISSION_RESOLV_FILE',
    }:
        raise ValueError('Unsupported bundle environment schema; update the deployer.')
    values.update({key: repo + ':latest' for key, repo in REPOS.items()})
    defaults = {
        'CONFIG_ROOT': str(destination / 'appdata'),
        'DOWNLOAD_ROOT': '/Volume1/SHARED/Movies/bobDownloads',
        'FILMS_ROOT': '/Volume1/SHARED/Movies/bobFilms',
        'TV_ROOT': '/Volume1/SHARED/Movies/bobTV',
    }
    for key, default in defaults.items():
        values[key] = ask(key, default, validate=absolute)
    disjoint([Path(values[k]) for k in defaults])
    for key in ('DOWNLOAD_ROOT', 'FILMS_ROOT', 'TV_ROOT'):
        p = Path(values[key])
        if p == destination or p in destination.parents or destination in p.parents:
            raise ValueError(f'{key} must be separate from the deployment directory.')
    # Existing TNAS Plex account, selected by the user; no new account required.
    values.update(MEDIA_UID='10001', MEDIA_GID='10002',
                  SEERR_UID='10001', SEERR_GID='10002')
    values['TZ'] = ask('Timezone', 'Europe/London')
    values['NAS_BIND_IP'] = '192.168.0.102'
    used_ports = set()
    for key, default in [('SONARR_PORT', '8989'), ('RADARR_PORT', '7878'),
                         ('PROWLARR_PORT', '9696'), ('SEERR_PORT', '5055'), ('PORTAL_PORT', '8088')]:
        values[key] = available_port(key, default, values['NAS_BIND_IP'], used_ports)
    write_portal(destination / 'portal', values)
    values.update(vpn_credentials)
    print('NordVPN credentials loaded from /home/ian/.nordvpn.')
    values['NORDVPN_COUNTRIES'] = 'Netherlands,Belgium,Germany,Jersey,Isle of Man'
    for key in ('TRANSMISSION_USER', 'TRANSMISSION_PASSWORD'):
        secret = key != 'NORDVPN_COUNTRIES'
        while True:
            value = ask(key + (' (Nord service credentials, not account login)'
                              if key.startswith('NORDVPN_SERVICE') else ''), default='ian' if key == 'TRANSMISSION_USER' else '', secret=secret, validate=dotenv)
            if 'PASSWORD' in key:
                if getpass.getpass('Confirm password: ') != value:
                    print('Passwords differ; try again.')
                    continue
            dotenv(value)
            values[key] = value
            break
    values['TRANSMISSION_RESOLV_FILE'] = str(destination / 'config/transmission-resolv.conf')
    print('\nPlanned directories:')
    for key in defaults:
        print(f'  {key}: {values[key]}')
    print('New directories will be created with the selected owners. Existing app config ownership stays unchanged; inaccessible pilot media directories get Plex ownership.')
    private_write(destination / '.env', ''.join(f'{key}={dotenv(values[key])}\n' for key in keys))
    resolver = Path(values['TRANSMISSION_RESOLV_FILE'])
    private_write(resolver, (destination / 'config/transmission-resolv.conf.example').read_text())
    # Bind-mounted resolver must be readable by the downloader's non-root account.
    os.chown(resolver, 0, int(values['MEDIA_GID']))
    resolver.chmod(0o640)
    config = Path(values['CONFIG_ROOT'])
    absolute(str(config))
    mkdirs(config)
    for service in SERVICES:
        prefix = 'SEERR' if service == 'seerr' else 'MEDIA'
        uid, gid = (int(values[prefix + suffix]) for suffix in ('_UID', '_GID'))
        if service == 'gluetun':
            uid, gid = 0, 0
        folder = config / service
        prepare_owned(folder, uid, gid, mode=0o700)
        if not access_as(folder, uid, gid, os.R_OK | os.W_OK | os.X_OK):
            raise ValueError(f'{folder}: selected app account lacks access; fix only this folder and retry validation manually.')
    uid, gid = int(values['MEDIA_UID']), int(values['MEDIA_GID'])
    media = [Path(values[k]) for k in ('DOWNLOAD_ROOT', 'FILMS_ROOT', 'TV_ROOT')]
    media.extend(Path(values['DOWNLOAD_ROOT']) / name for name in ('complete', 'incomplete'))
    inaccessible = []
    for folder in media:
        prepare_owned(folder, uid, gid)
        if not access_as(folder, uid, gid, os.R_OK | os.W_OK | os.X_OK):
            inaccessible.append(str(folder))
    if inaccessible:
        print('\nThe media account lacks access to these existing directories:')
        print('\n'.join(inaccessible))
        for folder in inaccessible:
            repair_media_owner(Path(folder), uid, gid)
    print('Private configuration saved; directories prepared. No Plex libraries were changed.')
    print('\nPreparation complete. TOS handles deployment and startup; no Docker commands were run.')
    print(f'TOS project directory: {destination}')
    print(f'Compose file: {destination / "compose.yaml"}')
    print(f'Private environment file: {destination / ".env"}')
    print('Load .env through the TOS project environment settings if it is not loaded automatically.')
    print('Keep Transmission behind Gluetun. Test VPN/DNS/IPv6 isolation before submitting downloads.')
    print('After TOS starts the apps, configure authentication, API keys, indexers and Plex in their UIs.')
    print(f'BOB2 HOME: http://{values["NAS_BIND_IP"]}:{values["PORTAL_PORT"]}')
    for name in ('SONARR', 'RADARR', 'PROWLARR', 'SEERR'):
        print(f'{name}: http://{values["NAS_BIND_IP"]}:{values[name + "_PORT"]}')
    print('Sonarr root: /data/media/tv; Radarr root: /data/media/movies; downloader: gluetun:9091.')
    print('See docs/deploy-terramaster.md. Plex and existing media have not been changed.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, tarfile.TarError, subprocess.SubprocessError) as error:
        if isinstance(error, subprocess.SubprocessError):
            print('A directory permission command failed; no automatic rollback performed.', file=sys.stderr)
        else:
            print(f'Stopped: {error}', file=sys.stderr)
        sys.exit(1)
    except (KeyboardInterrupt, EOFError):
        print('\nStopped. Completed files/directories are retained; no containers were started.', file=sys.stderr)
        sys.exit(1)
