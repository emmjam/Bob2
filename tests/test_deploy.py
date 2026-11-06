"""Offline tests for archive safety, private settings and restricted permissions."""
import importlib.util
import io
import os
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('deploy', Path(__file__).parents[1] / 'scripts/deploy.py')
deploy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deploy)


class DeploymentTests(unittest.TestCase):
    def archive(self, root, extra=None):
        archive = root / 'bundle.tar.gz'
        with tarfile.open(archive, 'w:gz') as out:
            for name, body in [('compose.yaml', 'services: {}'), ('.env.example', (Path(__file__).parents[1] / '.env.example').read_text()),
                               ('config/transmission-resolv.conf.example', 'nameserver 127.0.0.1')]:
                data = body.encode()
                entry = tarfile.TarInfo(name)
                entry.size = len(data)
                out.addfile(entry, io.BytesIO(data))
            if extra:
                out.addfile(extra)
        return archive

    def test_extract_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive = self.archive(root)
            target = root / 'deployment'
            deploy.extract(archive, target)
            self.assertEqual((target / 'compose.yaml').read_text(), 'services: {}')
            with self.assertRaises(ValueError):
                deploy.extract(archive, target)
            self.assertEqual((target / 'compose.yaml').read_text(), 'services: {}')

    def test_traversal_and_link_rejected_before_creation(self):
        for name, kind in [('../escape', tarfile.REGTYPE), ('config/link', tarfile.SYMTYPE),
                           ('/absolute', tarfile.REGTYPE), ('config/device', tarfile.CHRTYPE)]:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                member = tarfile.TarInfo(name)
                member.type = kind
                member.linkname = '/tmp'
                archive = self.archive(root, member)
                with self.assertRaises(ValueError):
                    deploy.extract(archive, root / 'deployment')
                self.assertFalse((root / 'deployment').exists())

    def test_symlink_destination_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'link').symlink_to(root, target_is_directory=True)
            with self.assertRaises(ValueError):
                deploy.extract(self.archive(root), root / 'link/deployment')

    def test_private_file_and_literal_credentials(self):
        self.assertEqual(deploy.dotenv("a$b#c 'd'"), "'a$b#c \\'d\\''")
        with self.assertRaises(ValueError):
            deploy.dotenv('trailing\\')
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / '.env'
            deploy.private_write(path, 'secret')
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                deploy.private_write(path, 'replacement')

    def test_existing_directory_not_modified(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            before = path.stat()
            with patch.object(os, 'chown') as chown:
                deploy.prepare_owned(path, 1234, 1234)
                chown.assert_not_called()
            self.assertEqual(path.stat().st_mode, before.st_mode)

    def test_disjoint_paths(self):
        with self.assertRaises(ValueError):
            deploy.disjoint([Path('/data'), Path('/data/media')])
        deploy.disjoint([Path('/config'), Path('/downloads'), Path('/films')])


    def test_github_wrapper_extraction(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive = self.archive(root)
            wrapped = root / 'github.tar.gz'
            with tarfile.open(archive) as source, tarfile.open(wrapped, 'w:gz') as output:
                for member in source.getmembers():
                    data = source.extractfile(member)
                    member.name = 'emmjam-Bob2-abc123/' + member.name
                    output.addfile(member, data)
            deploy.extract(wrapped, root / 'project', github=True)
            self.assertTrue((root / 'project/compose.yaml').is_file())

    def test_redirect_drops_token(self):
        req = deploy.urllib.request.Request('https://api.github.com/repos/emmjam/Bob2/tarball/main',
                                            headers={'Authorization': 'Bearer private'})
        handler = deploy.GitHubRedirect()
        redirected = handler.redirect_request(req, None, 302, '', {}, 'https://codeload.github.com/emmjam/Bob2/archive')
        self.assertIsNone(redirected.get_header('Authorization'))
        with self.assertRaises(ValueError):
            handler.redirect_request(req, None, 302, '', {}, 'https://example.com/archive')

    def test_complete_preparation_never_calls_docker(self):
        from contextlib import redirect_stdout
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive = self.archive(root)
            destination = root / 'deployment'

            def answer(label, default='', **kwargs):
                if label.startswith('Absolute path'):
                    return str(archive)
                if label.startswith('Absolute deployment'):
                    return str(destination)
                if label == 'GitHub repository':
                    return 'emmjam/Bob2'
                key = label.split(':')[0].split(' ')[0]
                if key in deploy.REPOS:
                    self.fail('Image defaults must not prompt the user')
                if key == 'CONFIG_ROOT':
                    return str(destination / 'appdata')
                if key in ('DOWNLOAD_ROOT', 'FILMS_ROOT', 'TV_ROOT'):
                    return str(root / key.lower())
                if key.endswith(('_UID', '_GID')):
                    return '1234'
                if key == 'NAS_BIND_IP':
                    return '192.168.1.2'
                if 'PASSWORD' in key:
                    return 'private$password'
                return default or 'test'

            original_extract = deploy.extract
            output = io.StringIO()
            with patch.object(deploy, 'download_bundle'), \
                    patch.object(deploy, 'extract', side_effect=lambda bundle, dest, **kw: original_extract(archive, dest)), \
                    patch.object(deploy, 'ask', side_effect=answer), \
                    patch.object(os, 'geteuid', return_value=0), \
                    patch.object(os, 'chown'), \
                    patch.object(deploy, 'access_as', return_value=True), \
                    patch.object(deploy.socket, 'socket'), \
                    patch.object(deploy.getpass, 'getpass', return_value='private$password'), \
                    patch('builtins.input', return_value='y'), \
                    patch.object(deploy.subprocess, 'run') as commands, redirect_stdout(output):
                deploy.main()
                commands.assert_not_called()
            self.assertTrue((destination / '.env').is_file())
            for key, repo in deploy.REPOS.items():
                self.assertIn(f"{key}='{repo}:latest'", (destination / '.env').read_text())
            self.assertTrue((destination / 'appdata/sonarr').is_dir())
            self.assertEqual((destination / 'appdata/sonarr').stat().st_mode & 0o777, 0o700)
            self.assertNotIn('private$password', output.getvalue())
            self.assertIn('TOS handles deployment', output.getvalue())


if __name__ == '__main__':
    unittest.main()
