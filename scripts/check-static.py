"""Offline template checks only; never contacts Docker, NAS or workers."""
from pathlib import Path
import re
import subprocess
import yaml

root = Path(__file__).resolve().parents[1]
raw = (root / 'compose.yaml').read_text()
c = yaml.safe_load(raw)
s = c['services']
assert set(s) == {'seerr', 'sonarr', 'radarr', 'prowlarr', 'transmission', 'gluetun'}
t = s['transmission']
assert t['network_mode'] == 'service:gluetun'
assert not any(k in t for k in ('ports', 'networks', 'dns', 'cap_add'))
assert t['depends_on']['gluetun'] == {'condition': 'service_healthy', 'restart': True}
g = s['gluetun']
assert g['environment']['FIREWALL'] == 'on'
assert g['ports'] == ['${NAS_BIND_IP:?Set NAS_BIND_IP in a private .env}:9091:9091']
assert g['environment']['VPN_SERVICE_PROVIDER'] == 'nordvpn'
assert g['environment']['VPN_TYPE'] == 'openvpn'
assert 'FIREWALL_OUTBOUND_SUBNETS' not in g['environment']
assert g['sysctls']['net.ipv6.conf.all.disable_ipv6'] == '1'
assert not c['networks']['media']['enable_ipv6']
assert s['seerr']['environment']['DB_TYPE'] == 'sqlite'
for name, service in s.items():
    assert '${' in service['image'] and ':?' in service['image']
    assert service.get('network_mode') != 'host'
    assert not service.get('privileged')
    for mount in service.get('volumes', []):
        assert mount['type'] == 'bind' and mount['bind']['create_host_path'] is False
    for port in service.get('ports', []):
        assert port.startswith('${NAS_BIND_IP:?')
resolver = next(v for v in t['volumes'] if v['target'] == '/etc/resolv.conf')
assert resolver['read_only'] is True
assert 'nameserver 127.0.0.1' in (root / 'config/transmission-resolv.conf.example').read_text()
required = set(re.findall(r'\$\{([A-Z_]+):\?', raw))
values = dict(line.split('=', 1) for line in (root / '.env.example').read_text().splitlines()
              if line and not line.startswith('#'))
assert required == set(values), (required - set(values), set(values) - required)
assert values['FILMS_ROOT'] == '/Volume1/SHARED/Movies/bobFilms'
assert values['TV_ROOT'] == '/Volume1/SHARED/Movies/bobTV'
assert all(v == '' for k, v in values.items() if k not in ('FILMS_ROOT', 'TV_ROOT'))
for name, key, target in [('sonarr', 'TV_ROOT', '/data/media/tv'),
                          ('radarr', 'FILMS_ROOT', '/data/media/movies')]:
    mounts = {v['target']: v['source'] for v in s[name]['volumes']}
    assert set(mounts) == {'/config', '/data/downloads', target}
    assert mounts[target].startswith('${' + key + ':?')
    assert mounts['/data/downloads'].startswith('${DOWNLOAD_ROOT:?')
assert next(v['source'] for v in t['volumes'] if v['target'] == '/data/downloads').startswith('${DOWNLOAD_ROOT:?')
for private in ('.env', '.env.pilot', 'private/settings.json', 'config/transmission-resolv.conf',
                'runtime/state', 'appdata/seerr/settings.json', 'backups/state.tar'):
    assert subprocess.run(['git', 'check-ignore', '-q', '--', private], cwd=root).returncode == 0, private
for template in ('.env.example', 'config/transmission-resolv.conf.example', 'compose.yaml'):
    assert subprocess.run(['git', 'check-ignore', '-q', '--', template], cwd=root).returncode == 1, template
for path in root.rglob('*'):
    if path.is_file() and not {'.git', '__pycache__'}.intersection(path.relative_to(root).parts):
        content = path.read_text()
        assert all(line == line.rstrip() for line in content.splitlines()), path
        if path.suffix == '.md':
            for target in re.findall(r'\]\(([^)]+)\)', content):
                if not target.startswith(('https://', 'http://', '#')):
                    assert (path.parent / target.split('#')[0]).exists(), (path, target)
print('PASS: six-service structure, VPN boundary, binds, required parameters and isolated pilot mounts, exclusions, links and whitespace.')
print('Static checks only: no Compose CLI, images, TOS or runtime acceptance.')
