# Production release checklist

MinScale packages are intended to run on routers that may carry real network
traffic. A smaller file or a successful startup is not enough to call a build
ready for use.

## Build inputs

- Pin an upstream Tailscale release and source commit. Record the source hash.
- Pin the Go toolchain, OpenWrt release, target, and cross toolchain.
- Record the exact feature tags and compare them with the profile's feature
  inventory.
- Build from a clean source tree. Keep private signing keys outside the repo
  and CI logs.
- Record package and executable hashes, Go build information, and build
  commands.

## Package checks

- Inspect the APK contents, dependencies, config ownership, init script, and
  upgrade behavior.
- Sign the APK with a key controlled by the operator and verify the signature
  on a clean OpenWrt installation.
- Confirm that installation replaces the official `tailscale` package cleanly
  and that rollback restores the previous service and state.
- Check the installed package size against the target's actual writable space.

## Device checks

Run these on the exact device and firmware intended for the release:

- Register with the control plane and reconnect after a daemon restart and a
  network interruption.
- Verify direct peer connectivity, DERP fallback, endpoint roaming, and
  WireGuard/TUN traffic.
- Verify DNS over UDP and TCP for IPv4 and IPv6 where the platform supports
  those paths.
- Test TCP in both directions, UDP, and parallel streams; record throughput,
  CPU, RSS, `RssAnon`, and Go runtime metrics.
- Check memory recovery after traffic bursts and run a soak with periodic load.
- Confirm there are no OOM kills, unexpected restarts, or loss of routing and
  DNS service.
- Keep a rollback path available during the test.

## Publish

- Publish only a build that passed the checks above on its declared target.
- Attach a checksum file and a concise test report to the release.
- State the supported device/firmware matrix and every intentionally omitted
  feature.
- Do not describe an unsigned test APK or an untested profile as production
  ready.
