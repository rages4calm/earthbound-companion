# SPDX-License-Identifier: GPL-3.0-or-later
"""ROM-free TLS regressions; cryptography is a test-only dependency."""
from contextlib import contextmanager
import datetime
import http.server
import io
from pathlib import Path
import ssl
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

import redux_setup_entry as setup


@contextmanager
def local_https():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'localhost')])
    now = datetime.datetime.now(datetime.timezone.utc)
    certificate = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
        .public_key(key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=1))
        .not_valid_after(now + datetime.timedelta(days=1))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName('localhost')]), critical=False)
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(key, hashes.SHA256()))
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'tls-fixture')
        def log_message(self, *_):
            pass
    with tempfile.TemporaryDirectory() as temporary:
        cert = Path(temporary) / 'cert.pem'
        private = Path(temporary) / 'key.pem'
        cert.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
        private.write_bytes(key.private_bytes(serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        server = http.server.HTTPServer(('127.0.0.1', 0), Handler)
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls.load_cert_chain(cert, private)
        server.socket = tls.wrap_socket(server.socket, server_side=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield cert, server.server_port
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)


def empty_system_context():
    # Reproduce a frozen interpreter whose build-machine CA paths are absent.
    return ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)


def fetch(url, context):
    # Loopback fixtures must not go through any machine-wide HTTP proxy.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}),
        urllib.request.HTTPSHandler(context=context))
    with opener.open(url, timeout=3) as response:
        return response.read()


class SourceTlsTests(unittest.TestCase):
    def test_download_uses_verified_context_and_rejects_wrong_archive(self):
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(setup.urllib.request, 'urlopen', return_value=io.BytesIO(b'wrong archive')) as opened:
                with self.assertRaisesRegex(ValueError, 'checksum'):
                    setup.download_source(Path(temporary) / 'source.zip')
            context = opened.call_args.kwargs['context']
            self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
            self.assertTrue(context.check_hostname)

    def test_empty_system_trust_gains_bundled_roots_and_stays_verified(self):
        with patch.object(setup.ssl, 'create_default_context', side_effect=empty_system_context):
            context = setup.source_download_context()
        self.assertGreater(context.cert_store_stats()['x509_ca'], 0)
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(context.check_hostname)

    def test_missing_bundled_roots_fails_instead_of_disabling_verification(self):
        with patch('certifi.where', return_value='/nonexistent/redux-ca-fixture.pem'):
            with self.assertRaises(FileNotFoundError):
                setup.source_download_context()

    def test_untrusted_server_is_rejected(self):
        with local_https() as (_, port):
            with self.assertRaises(urllib.error.URLError) as failure:
                fetch(f'https://localhost:{port}', setup.source_download_context())
            self.assertIsInstance(failure.exception.reason, ssl.SSLCertVerificationError)

    def test_existing_local_trust_is_preserved(self):
        with local_https() as (cert, port):
            context = empty_system_context()
            context.load_verify_locations(cafile=cert)
            with patch.object(setup.ssl, 'create_default_context', return_value=context):
                combined = setup.source_download_context()
            self.assertEqual(fetch(f'https://localhost:{port}', combined), b'tls-fixture')

    def test_trusted_certificate_for_wrong_hostname_is_rejected(self):
        with local_https() as (cert, port):
            context = empty_system_context()
            context.load_verify_locations(cafile=cert)
            with patch.object(setup.ssl, 'create_default_context', return_value=context):
                combined = setup.source_download_context()
            with self.assertRaises(urllib.error.URLError) as failure:
                fetch(f'https://127.0.0.1:{port}', combined)
            self.assertIsInstance(failure.exception.reason, ssl.SSLCertVerificationError)


if __name__ == '__main__':
    unittest.main()
