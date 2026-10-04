# Rebuilding the stage 3 evaluation packages

This directory contains the selected build recipe, the existing r3 low-memory
patches, the one new control decoder patch, and the OpenWrt packaging scripts.
It does not contain router state, registration credentials or signing keys.
Nothing here uploads a release or modifies a router.

The tested target is BT-RB300, MT7981, ARM64 v8.0, OpenWrt 25.12.5,
Linux 6.12.94. These are local evaluation packages from a development snapshot,
not a new supported Tailscale release. The package version retains the r3
snapshot prefix and increments its package revision to r4; the programs report
`1.103.0-dev20260926-t2e67abd7d`.

## Build the programs

Use a Linux build host with Python 3, Git, patch, and network access. The source
wrapper downloads the exact Tailscale Go toolchain recorded in `inputs.json`.
The script checks out the pinned upstream base, imports the small Git bundle
containing the four existing profile commits, and verifies the result. The
upstream version tag is fetched too: Go uses it when stamping the module version.

```sh
python3 build.py --work /absolute/path/to/new-build --jobs 4 --test
```

The output is `new-build/artifacts/tailscaled-arm64` and `tailscale-arm64`.
`build-results.json` contains their sizes, hashes, commands and Go build metadata.
Daemon and CLI tag lists are separate and both match their r3 counterparts.

The WireGuard module is copied and patched privately. The source checkout stays
clean; the zstd change is supplied through a Go source overlay. An overlay patch
is not part of the revision shown by `tailscale version`, so keep the supplied
patches and build manifest with any resulting package.

The daemon records the absolute replacement-module path in its Go metadata.
Changing the build directory changes its hash and can change ELF layout. The
measured build used `/home/uni/minscale-stage3-20261003`. A fresh checkout with
the original unchanged module at that same path reproduced the measured daemon
hash exactly. The CLI reproduced exactly in an independent directory. See
`exact-path-check.json`; do not mistake a path-dependent hash for a source change.

## Package either storage format

Use an OpenWrt 25.12.5 SDK with working host `apk` and SDK `fakeroot`, plus
SquashFS tools 4.6.1 for compact. Keep the private signing key outside this
directory. `KEYS` below is a directory containing its matching public key.

```sh
python3 package.py \
  --work /absolute/path/to/new-package-output \
  --artifacts /absolute/path/to/new-build/artifacts \
  --sdk-host /absolute/path/to/sdk/staging_dir/host \
  --sign-key "$SIGNING_KEY" --keys-dir "$KEYS" \
  --compact-block 64
```

The compact package stores the unmodified daemon and CLI in an XZ SquashFS image
with 64 KiB blocks. It mounts that image at boot, before tailscaled starts. Both
programs execute from the read-only filesystem. It requires matching OpenWrt
`kmod-loop` and `kmod-fs-squashfs`, XZ support and the `flock` applet. Dependencies
are required even when this particular firmware has the drivers built in.
Never install a kmod compiled for a different kernel ABI.

For the alternative plain package, omit `--compact-block` and pass
`--cli-upx --upx /absolute/path/to/upx`. The measured version was UPX 5.2.1.
Only the CLI is packed. The packager tests it and verifies that decompression
recreates the original bytes. This saves space without making the running
daemon's executable pages anonymous, but each CLI invocation has decompression
cost. The daemon is identical in both formats.

Each invocation needs a fresh output directory. Results and the signed APK are
under its `delivery/` directory. The two formats have the same package name and
revision and are alternatives, not packages to install together. Packaging the
measured input ELFs through this portable recipe reproduced the SquashFS image
hash exactly; APK hashes differ because package filesystem timestamps are not
normalized by this recipe.

## Configuration and checks

The selected runtime settings remain the tested r3 values:

```text
config settings 'settings'
        option gogc '10'
        option gomemlimit '24MiB'
```

These are entries in `/etc/config/tailscale`, not shell exports appended to the
init script. Existing UCI configuration is preserved across upgrades. Confirm
the actual procd environment after installing. GOMEMLIMIT is a soft Go-managed
memory limit; it is not an RSS cap. The 12 MiB limit and disabled-inlining
experiments increased GC cost and were not selected.

Copy the verified signing public key into the router's APK trust store before
installing a package. Verify the package signature with that key. Keep the
previous APK and a private backup of `/etc/tailscale` and `/etc/config/tailscale`
for rollback. The package hooks preserve state, but state backups are private
and must never be included in build artifacts.

The measured lifecycle includes plain/compact replacement, concurrent CLI
startup, CLI use while the service is stopped, uninstall with an open executable
reference, and reinstalling r3 with the same registration. A reboot mounts the
compact image and starts procd automatically.

The test firmware also starts mwan3. Its routing rules intercepted tailnet and
MagicDNS traffic after reboot. Exact-address temporary test rules restored the
paths without restarting tailscaled. This is not fixed by the package. A real
deployment must integrate its Tailscale routes with the router's own mwan3 and
firewall configuration; do not copy the test peer's addresses as a general fix.

The feature boundary remains LowMem r3, not the complete upstream daemon:
kernel TUN/WireGuard, control compatibility, direct discovery, DERP, IPv4/IPv6,
DNS transport, routing and the existing ACL code remain. The profile continues
to omit Tailscale SSH, Serve/Funnel, Taildrop/Drive, web UI, cloud integrations,
the updater and much of debugging/logging. The exact two tag manifests are the
authoritative build inventory. This stage removes no additional feature.

Before publishing a rebuilt package, repeat the device tests from the main
report against its exact hash. The tests here do not establish exit-node/subnet
throughput or endpoint-roaming coverage, and this stage used Headscale rather
than a Tailscale-hosted control server.
