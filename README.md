# MinScale

MinScale explores smaller Tailscale builds for OpenWrt routers with tight RAM
and flash budgets. It builds upstream `tailscaled` with an explicit feature
profile, packages it for OpenWrt, and records what was tested on real devices.

MinScale is not a new VPN client or protocol. It is an independent community
project and is not affiliated with Tailscale, Inc. Each profile documents the
features it leaves out; compatibility with the control plane does not imply
full feature parity with the standard client.

## Status

There is no production release yet. MinScale tracks two separate experiments:
a two-hour RAM study on an ARM64 MT7981 router and a short package-size study
on a MIPS Cudy TR1200. The RAM profile has not been ported or benchmarked on the
TR1200. The size experiment used Tailscale v1.98.3 and did not cover DNS,
sustained traffic, reconnect recovery, or a long soak. Its test package was
unsigned and is not suitable for production installation.

See the [MT7981 memory study](docs/experiments/MT7981-memory-2026-09.md) and
[TR1200 size experiment](docs/experiments/TR1200-v1.98.3.md) for the device-
specific results and limitations. The historical MIPS build script only
reproduces the size experiment; it does not enable the memory changes or
produce a supported release.

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

The separate MT7981 study measured a 25.22 MiB connected-idle RSS median after
a two-hour workload, compared with 41.75 MiB for the full upstream build and
39.28 MiB for upstream with `GOGC=10`. That result came from a custom ARM64
profile with code changes and runtime settings. It is not a result for the
TR1200 MIPS build. The current MIPS recipe does not set `GOGC` or `GOMEMLIMIT`.

No package binaries are stored in Git. Future release artifacts should be
published with checksums, source and toolchain provenance, and signing details.
