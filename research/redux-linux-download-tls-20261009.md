# Redux desktop source-download TLS report

A Linux community tester reports that Original works, while Redux stops at
`download-source` with `CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate`.
This failure precedes source extraction, ROM compilation and asset conversion.
The tester's distro, trust configuration and exact preview version are unknown.

The helper used urllib's implicit default SSL context. Frozen Python/OpenSSL
can retain certificate paths from its build environment that are absent on the
player's machine. The report is consistent with unavailable public trust roots;
it does not prove a specific distro problem or exclude a custom HTTPS proxy.

## Local change

- Build a normal verified SSL context retaining system/local trust, then load
  Certifi's packaged Mozilla public roots. Certificate and hostname verification
  remain enabled. The pinned archive SHA-256 and size bound remain enforced.
- Explicitly include Certifi's module/data in the frozen helper. The portable
  helper build installs it and copies its license into the package notices.
- Add `--selftest-source-download`: a ROM-free check of the same HTTPS download
  and exact pinned archive checksum, using a temporary directory removed on exit.
- Prepare desktop CI to run six TLS regressions and the actual packaged download
  with nonexistent SSL_CERT_FILE/SSL_CERT_DIR paths on Linux and macOS.

Certifi source/license: https://github.com/certifi/python-certifi .
Python SSL context semantics: https://docs.python.org/3/library/ssl.html .

## Executed evidence and limits

On the owner's Windows host, all six tests pass: empty system trust gains public
roots; verification remains required; missing bundle fails; an untrusted local
TLS server is rejected; existing local trust remains usable; wrong hostnames are
rejected; and an altered download fails its checksum. The checksum/context test
is one of the six cases.

The source-mode selftest downloaded the pinned archive and verified its checksum.
An isolated PyInstaller helper build also passed the same selftest with invalid
certificate-path environment settings. Certifi 2026.4.22 and PyInstaller 6.22.3
were used for this local package check. Windows can additionally use its own
certificate store; the empty-trust unit regression separately tests loading the
bundled roots without that store.

Private build receipts are outside the worktree at
`_BuildScratch/multiplatform/redux-tls-fix`. This Windows helper is a packaging
check, not a Linux download for the tester. No Linux/macOS rebuilt executable,
full Redux compilation, or tester retest has been executed for this change.
Prepared CI has not run: the owner's no-push instruction remains active.

No release, PR update, Windows installation replacement, ROM/pack publication
or player-save change was performed. The next verification is the rebuilt Linux
helper's source-download check followed by the reporter's Redux setup retry.

The owner subsequently authorized pushing this focused TLS fix to the platform
preview branch. The preceding results describe the local checkpoint before that
push; they do not claim execution of GitHub CI or delivery of new preview assets.
The separate Deluxe investigation remains private.
