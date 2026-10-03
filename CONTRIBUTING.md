# Contributing

MinScale changes should include the exact upstream Tailscale version, OpenWrt
target and toolchain, build tags, and commands used. For device results, include
the router model, firmware/kernel version, test conditions, and raw measurements
where practical.

Do not attach Tailscale state files, auth keys, control-server keys, private
signing keys, or unredacted logs. Router logs and profiles can contain private
addresses and node details; review them before sharing.

Feature removals need an explicit description of what stops working. A build
profile is not ready to be called production-ready until it passes the checks
in `docs/RELEASE-CHECKLIST.md` on its declared target.
