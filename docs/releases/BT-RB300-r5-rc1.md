# BT-RB300 r5 test prerelease

This is the signed MinScale LowMem r5 compact package measured on a Globitel
BT-RB300 (MT7981, ARM64, 256 MB RAM) running OpenWrt 25.12.5, kernel 6.12.94.
It is built from the same pinned Tailscale development snapshot and LowMem
feature profile as r4. The package revision adds an opt-in `mwan3` startup
setting; it does not claim to be a general OpenWrt package.

The APK SHA-256 is
`5a97a8ac062c1f1addd8a8b743645379c20aebf32928be0b749c9fe7f052954a`.
The installed daemon SHA-256 is
`155780c67f2fc55d9bff9c50403cb383e6750a15bce8db2ecfbb46e698b0b49c`.
The APK is 9,914,657 bytes; the uncompressed daemon executable is 18,415,776
bytes. The APK uses XZ SquashFS to save storage. Package size and RSS are
different measurements.

## Why r5 exists

On this router, `tailscaled` sometimes started before `mwan3` installed its
policy rules. Tailscale then selected priorities 52xx. Later, `mwan3`'s rule
2001 intercepted Tailnet and MagicDNS traffic. Restarting the daemon after
`mwan3` started selected Tailscale's existing 13xx priorities and restored
connectivity. This boot race was already described in
[Tailscale issue #12667](https://github.com/tailscale/tailscale/issues/12667).

r5 adds `option mwan3_compat '0'` to the OpenWrt config. If the router uses
`mwan3`, setting `tailscale.settings.mwan3_compat=1` tells the daemon to use
the existing 13xx priorities from startup. The option is off by default.
After a real reboot with the option enabled, the BT-RB300 had IPv4 and IPv6
Tailscale rules 1310/1330/1350/1370 and `mwan3` rule 2001. No temporary
address-specific rules were present. Direct connectivity, TSMP, and actual
MagicDNS queries over UDP/TCP on both IPv4 and IPv6 passed. TCP and UDP passed
in both directions.

## Two-hour soak

The exact installed r5 APK completed 7,200 seconds with seven mixed TCP/UDP
bursts at 15-minute spacing. The last 20 minutes had no traffic burst.
All 481 `/proc` and Go runtime samples were present and belonged to one
PID/start-time identity. The daemon hash still matched the APK at the end.
No OOM kill or panic appeared in the collected logs.

| Measurement | r5 result |
| --- | ---: |
| Peak RSS during soak | 27.28 MiB |
| Final 20-minute median RSS | 25.46 MiB |
| Final median RssAnon / RssFile | 8.38 / 17.08 MiB |
| Final median HeapAlloc / HeapLive | 3.05 / 2.73 MiB |
| Final median goroutines | 66 |
| Whole-run Go GC CPU | 0.056% of one core |

Four-stream TCP over the seven bursts ranged from 255 to 279 Mbit/s in the
receive direction and 338 to 376 Mbit/s in the transmit direction. UDP at a
100 Mbit/s target delivered about 100 Mbit/s receive and 95 to 99 Mbit/s
transmit. Transmit-direction UDP loss ranged from 0.97% to 4.60% under that
load. Direct peer connectivity, TSMP, and actual DNS queries over UDP/TCP on
IPv4/IPv6 passed both before and after the soak.

The final quiet median is 0.19 MiB above r4's separate 25.27 MiB soak on the
same router. This small difference is not evidence that the routing patch
caused a memory regression. The two runs are observations of different
process lifetimes and network activity. The r5 data show recovery after each
burst, not a proof of unlimited uptime. PSS was unavailable on this kernel.

## Scope

This build retains the r4 LowMem router feature profile: TUN/WireGuard,
direct discovery, DERP, IPv4/IPv6, DNS transport, routing, and ACL processing.
It omits Tailscale SSH, Serve/Funnel, Taildrop/Drive, web UI, cloud
integrations, the updater, and much of the debug/logging surface. The exact
feature tags and source patches are in the attached recipe and the
[`bt-rb300-r5` profile](https://github.com/unisequence/MinScale/tree/main/profiles/bt-rb300-r5).

This package was tested with Headscale. The Tailscale-hosted control plane,
WAN failover, routed subnet and exit-node throughput, endpoint roaming, and
large tailnets were not validated in this run. On routers without `mwan3`,
leave `mwan3_compat` disabled. On other `mwan3` configurations, verify policy
rule order, underlay connectivity, DNS, and routes after reboot. This is a
BT-RB300 test prerelease, not a universal firmware replacement.

The compact package requires `ca-bundle`, `kmod-tun`, `kmod-loop`, and
`kmod-fs-squashfs` for the installed kernel. Check the kernel ABI before
installing any kmod. Save the previous APK and make a private backup of
`/etc/tailscale` and `/etc/config/tailscale`; keep a rollback path. Verify
the APK against `SHA256SUMS` and the attached public key. Do not install it
alongside the official package because both own `/usr/sbin/tailscale*`.
