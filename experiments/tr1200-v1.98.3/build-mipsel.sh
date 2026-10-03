#!/bin/sh
set -eu

TS_REPO=${TS_REPO:?Set TS_REPO to a Tailscale checkout containing tag v1.98.3}
OPENWRT_DIR=${OPENWRT_DIR:?Set OPENWRT_DIR to an OpenWrt 25.12.5 tree with the MIPS toolchain}
UPX_BIN=${UPX_BIN:-upx}
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
OUT_DIR=${OUT_DIR:-"$SCRIPT_DIR/artifacts"}
BUILD_ROOT=${BUILD_ROOT:-$(mktemp -d "${TMPDIR:-/tmp}/tailscale-tr1200-build.XXXXXX")}

VERSION=1.98.3
PACKAGE_VERSION=1.98.3-r1
GO_VERSION=go1.26.8
TOOLCHAIN="$OPENWRT_DIR/staging_dir/toolchain-mipsel_24kc_gcc-14.3.0_musl"
HOST_APK="$OPENWRT_DIR/staging_dir/host/bin/apk"
TARGET_CC="$TOOLCHAIN/bin/mipsel-openwrt-linux-musl-gcc"
TARGET_STRIP="$TOOLCHAIN/bin/mipsel-openwrt-linux-musl-strip"
PACKAGE_FILES="$OPENWRT_DIR/feeds/packages/net/tailscale/files"
SOURCE_DIR="$BUILD_ROOT/source"
PACKAGE_ROOT="$BUILD_ROOT/package-root"
OUTPUT_APK="$OUT_DIR/tailscale-small-$PACKAGE_VERSION-mipsel_24kc-upx.apk"

KEEP_FEATURES=cli,dns,osrouter,useroutes,useexitnode,advertiseroutes,advertiseexitnode,portmapper,logtail,health,ipnbus,listenrawdisco,portlist,tundevstats,bakedroots,tailnetlock,ace,useproxy,peerapiclient,peerapiserver,syslog,unixsocketidentity

for required in go git tar fakeroot sha256sum; do
	command -v "$required" >/dev/null 2>&1 || {
		echo "missing required command: $required" >&2
		exit 1
	}
done
for required_file in "$TARGET_CC" "$TARGET_STRIP" "$HOST_APK" \
	"$PACKAGE_FILES/tailscale.init" "$PACKAGE_FILES/tailscale.conf"; do
	[ -e "$required_file" ] || {
		echo "missing required file: $required_file" >&2
		exit 1
	}
done
"$UPX_BIN" --version | grep -q 'upx 5\.2\.1' || {
	echo "this experiment was measured with UPX 5.2.1; set UPX_BIN to that version" >&2
	exit 1
}

mkdir -p "$SOURCE_DIR" "$OUT_DIR"
git -C "$TS_REPO" rev-parse --verify "refs/tags/v$VERSION^{commit}" >/dev/null || {
	echo "missing Tailscale tag v$VERSION in TS_REPO" >&2
	exit 1
}
git -C "$TS_REPO" archive --format=tar "v$VERSION" | tar -xf - -C "$SOURCE_DIR"

BUILD_TAGS=$(cd "$SOURCE_DIR" && GOTOOLCHAIN="$GO_VERSION" go run ./cmd/featuretags --min --add="$KEEP_FEATURES")
printf 'Build tags: %s\n' "$BUILD_TAGS"

cd "$SOURCE_DIR"
env STAGING_DIR="$OPENWRT_DIR/staging_dir" \
	GOOS=linux GOARCH=mipsle GOMIPS=softfloat CGO_ENABLED=1 \
	CC="$TARGET_CC" \
	CGO_CFLAGS='-Os -pipe -march=24kc -mno-mips16 -msoft-float' \
	GOTOOLCHAIN="$GO_VERSION" \
	go build -trimpath -buildvcs=false -installsuffix=softfloat \
	-tags="$BUILD_TAGS" \
	-ldflags="-linkmode external -X tailscale.com/version.shortStamp=$VERSION -X tailscale.com/version.longStamp=$VERSION-1" \
	-o "$BUILD_ROOT/tailscaled" ./cmd/tailscaled

"$TARGET_STRIP" --strip-all "$BUILD_ROOT/tailscaled"
"$UPX_BIN" --best --lzma -o "$BUILD_ROOT/tailscaled-upx" "$BUILD_ROOT/tailscaled"

mkdir -p "$PACKAGE_ROOT/usr/sbin" "$PACKAGE_ROOT/etc/init.d" \
	"$PACKAGE_ROOT/etc/config" "$PACKAGE_ROOT/lib/upgrade/keep.d" \
	"$PACKAGE_ROOT/lib/apk/packages"
install -m 0755 "$BUILD_ROOT/tailscaled-upx" "$PACKAGE_ROOT/usr/sbin/tailscaled"
ln -sf tailscaled "$PACKAGE_ROOT/usr/sbin/tailscale"
install -m 0755 "$PACKAGE_FILES/tailscale.init" "$PACKAGE_ROOT/etc/init.d/tailscale"
install -m 0644 "$PACKAGE_FILES/tailscale.conf" "$PACKAGE_ROOT/etc/config/tailscale"
printf '/etc/tailscale/\n' > "$PACKAGE_ROOT/lib/upgrade/keep.d/tailscale"
printf '%s\n' \
	/etc/config/tailscale \
	/etc/init.d/tailscale \
	/lib/upgrade/keep.d/tailscale \
	/usr/sbin/tailscale \
	/usr/sbin/tailscaled \
	> "$PACKAGE_ROOT/lib/apk/packages/tailscale-small.list"
printf '%s\n' /etc/config/tailscale /etc/tailscale/ \
	> "$PACKAGE_ROOT/lib/apk/packages/tailscale-small.conffiles"
CONFIG_HASH=$(sha256sum "$PACKAGE_ROOT/etc/config/tailscale" | cut -d ' ' -f 1)
printf '/etc/config/tailscale %s\n' "$CONFIG_HASH" \
	> "$PACKAGE_ROOT/lib/apk/packages/tailscale-small.conffiles_static"

fakeroot sh -c '
	chown -R 0:0 "$1"
	shift
	exec env SOURCE_DATE_EPOCH=0 "$@"
' sh "$PACKAGE_ROOT" "$HOST_APK" mkpkg \
	--compat 3.0 \
	--info "name:tailscale-small" \
	--info "version:$PACKAGE_VERSION" \
	--info "description:Tailscale size-reduction test build for Cudy TR1200" \
	--info "arch:mipsel_24kc" \
	--info "license:BSD-3-Clause" \
	--info "origin:minscale" \
	--info "url:https://tailscale.com" \
	--info "maintainer:local experiment" \
	--info "provides:tailscaled" \
	--info "depends:ca-bundle kmod-tun" \
	--files "$PACKAGE_ROOT" \
	--output "$OUTPUT_APK"

stat -c '%s bytes %n' "$BUILD_ROOT/tailscaled" "$BUILD_ROOT/tailscaled-upx" "$OUTPUT_APK"
sha256sum "$OUTPUT_APK"
printf 'Build workspace: %s\n' "$BUILD_ROOT"
