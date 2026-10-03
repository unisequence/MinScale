# Project status

MinScale is in the build-profile and validation stage. The MT7981 study
measured a lower-RSS ARM64 build; the separate TR1200 v1.98.3 study measured a
smaller MIPS package and a short connection smoke test. These are different
builds on different hardware. The ARM64 memory changes have not been ported to
or tested on the TR1200.

The historical TR1200 APK is unsigned and lacks sustained traffic, DNS,
reconnect, and soak tests. The next release candidate should use a current
upstream release and must be tested on a device that can be safely restarted.
No device install, service restart, or traffic test is part of the current
repository setup.

There is no supported MinScale package release at this time.
