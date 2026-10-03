# MinScale

MinScale explores smaller Tailscale builds for OpenWrt routers with tight RAM
and flash budgets. It builds upstream `tailscaled` with an explicit feature
profile, packages it for OpenWrt, and records what was tested on real devices.

MinScale is not a new VPN client or protocol. It is an independent community
project and is not affiliated with Tailscale, Inc. Each profile documents the
features it leaves out; compatibility with the control plane does not imply
full feature parity with the standard client.

## Status

There is no production release yet. The only device study currently recorded
is a short experiment on a Cudy TR1200 using Tailscale v1.98.3. It showed that
feature selection and UPX can reduce the package size, but it did not cover
DNS operation, sustained traffic, reconnect recovery, or a long soak. The test
package was unsigned and is not suitable for production installation.

See [the TR1200 experiment](docs/experiments/TR1200-v1.98.3.md) for the exact
measurements and limitations. The historical build script is kept only to
reproduce that experiment. It does not produce a supported release.

## Goals

- Keep ordinary Tailscale and Headscale control-plane compatibility.
- Preserve the router features needed for normal mesh networking, including
  TUN/WireGuard, DNS, direct connections, DERP, routes, and subnet routing
  where the selected build profile supports them.
- Reduce executable and package size without hiding removed features.
- Measure RAM, CPU, startup time, and network behavior on the target hardware.
- Keep builds tied to pinned upstream source and OpenWrt toolchains.

The project will not maintain a separate protocol implementation. Changes that
benefit all Tailscale users belong upstream; MinScale focuses on embedded build
profiles, packaging, and reproducible measurements.

## Production use

Do not deploy the historical test package from the experiment as a production
build. Before a MinScale package is marked for production, it needs a current
upstream base, a pinned and reviewable build environment, a package signature,
and the target-device checks in [the release checklist](docs/RELEASE-CHECKLIST.md).

Custom packages install files under the same `/usr/sbin/tailscale*` paths as
the official OpenWrt package. Remove the other package before installing a
MinScale build; do not install both at once.

The license in this repository covers MinScale-maintained files only. Tailscale
and OpenWrt components keep their own licenses.

## Historical experiment

On the TR1200, the tested feature profile produced a 17.85 MB stripped daemon.
UPX reduced it to 4.04 MB and the test APK to 4.04 MB, compared with a 9.79 MB
official APK. On the router, `tailscaled --version` took 2.84 seconds of user
CPU with UPX and 0.06 seconds with the unpacked executable. These are results
for that v1.98.3 build, not promises about later versions or other devices.

No package binaries are stored in Git. Future release artifacts should be
published with checksums, source and toolchain provenance, and signing details.
