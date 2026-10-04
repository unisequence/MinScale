# Project status

The BT-RB300 r4 package is a signed prerelease built from a pinned Tailscale
development snapshot. On OpenWrt 25.12.5 it passed a two-hour traffic soak,
package lifecycle checks, direct and DERP connectivity, and DNS transport tests.
Its final quiet-interval median was 25.27 MiB RSS. See the
[release report](releases/BT-RB300-r4-rc1.md) for the exact firmware and limits.

The separate TR1200 v1.98.3 study measured a smaller MIPS package and a short
connection smoke test. The ARM64 profile has not been ported to the TR1200.

The historical TR1200 APK is unsigned and lacks sustained traffic, DNS,
reconnect, and soak tests. The BT-RB300 package is an evaluation build, not a
supported production release. It was not tested with the Tailscale-hosted
control plane, endpoint roaming, or routed subnet/exit-node throughput. The
test firmware's `mwan3` rules also need separate route integration after reboot.

There is no supported production MinScale package release at this time.
