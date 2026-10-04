# BT-RB300 r4 release candidate

This is the compact MinScale LowMem r4 build measured on a Globitel BT-RB300
(MT7981, ARM64, 256 MB RAM) running OpenWrt 25.12.5, kernel 6.12.94, with
kernel TUN. The APK architecture is `aarch64_cortex-a53`. It is a prerelease
for this tested setup, built from a pinned Tailscale development snapshot
reporting `1.103.0-dev20260926-t2e67abd7d`. It has not been validated as a
general replacement for the OpenWrt `tailscale` package.

The [build recipe](../../profiles/bt-rb300-r4) records the source commits, Go
1.27.1 toolchain, feature tags, WireGuard patches, OpenWrt package template,
and build commands. The signed APK, public signing key, checksums, and this
report are release assets. The tested APK SHA-256 is
`29515f9fadaeb8dfd8b9ac5f7029514f19703ba2012d8c2017607768c090f3d5`.
The installed daemon SHA-256 is
`f0a9d6630333a007a71a2eecdb53a36499a4dfbaa051cc9e2e6463c8411d10e6`.
The APK is 9,914,742 bytes; it mounts an XZ SquashFS image containing the
unpacked daemon and CLI. The daemon executable itself is 18,415,776 bytes.
The compressed package size is a storage result, not the daemon's RSS.

## What was measured

The router was connected to Headscale with five peers. The comparison used the
same BT-RB300, firmware, wired test peer, and runtime settings for the existing
LowMem r3 package and this r4 package (`GOGC=10`, `GOMEMLIMIT=24MiB`).

| Installed package | RSS after traffic and 300 s quiet | TCP RX / TX | Four-stream TCP RX / TX |
| --- | ---: | ---: | ---: |
| LowMem r3 | 25.47 MiB | 319.2 / 388.8 Mbit/s | 276.1 / 352.2 Mbit/s |
| r4 compact | 24.95 MiB | 314.6 / 389.5 Mbit/s | 274.8 / 352.2 Mbit/s |

The exact installed r4 package then ran for two hours with seven TCP/UDP load
bursts and a final 20-minute quiet interval. It kept the same process identity
through all 481 samples. Peak RSS was 27.41 MiB; the final quiet median was
25.27 MiB, including 8.18 MiB `RssAnon` and 17.09 MiB `RssFile`. Final median
`HeapAlloc` was 2.98 MiB with 66 goroutines. Whole-run GC CPU was 0.054% of
one core. The collected logs showed no OOM kill or panic. This is a two-hour
observation, not a claim about indefinite uptime.

Direct peer connectivity, TSMP, WireGuard/TUN traffic, bidirectional TCP,
parallel TCP, UDP, DERP fallback, and reconnection after a down/up cycle were
checked. Real DNS queries over UDP and TCP on both IPv4 and IPv6 passed before
and after the soak. Package installation, CLI use, removal, reinstall, and
automatic image mount/service start after reboot were also exercised. The
signed APK was verified with its matching public key. PSS was unavailable
because this kernel exposes neither `smaps` nor `pagemap`.

## Installation scope and limits

This build keeps the LowMem r3 router feature profile: TUN/WireGuard, direct
discovery, DERP, IPv4/IPv6, DNS transport, routing, and ACL processing remain.
It omits Tailscale SSH, Serve/Funnel, Taildrop/Drive, web UI, cloud
integrations, the updater, and much of the debug/logging surface. The exact
daemon and CLI feature tags are in the recipe.

The compact package requires `ca-bundle`, `kmod-tun`, `kmod-loop`, and
`kmod-fs-squashfs` built for the installed kernel. Its `flock` helper and XZ
SquashFS support are needed at startup. Keep a copy of the current package and
a private backup of `/etc/tailscale` and `/etc/config/tailscale` before
replacement. The custom package uses the same `/usr/sbin/tailscale*` paths as
the official package, so remove the other package rather than installing both.
Verify the downloaded APK against `SHA256SUMS`, place the supplied public PEM
in `/etc/apk/keys/`, and run `apk verify` before installation. Do not publish
the router state file or a private signing key.

On the test firmware, `mwan3` started after reboot and its marked routes
intercepted locally generated Tailnet and MagicDNS traffic before Tailscale's
table 52. Temporary address-specific test rules restored the paths, but they
are not part of this APK. A router using `mwan3` needs its own routing
integration; simply installing the package does not fix that conflict.

This run used Headscale. It did not test the Tailscale-hosted control plane,
endpoint roaming, routed subnet or exit-node throughput, or large tailnets.
The previous r3-to-r4 package lifecycle checks were completed before the final
same-source CLI refresh; the final signed package passed signature verification
and native networking smoke tests. The build recipe can reproduce the source
and package image, but the daemon embeds the absolute path of its local
WireGuard replacement module, so changing that path can change the ELF hash.
Do not treat a different rebuild as the exact artifact measured here.
