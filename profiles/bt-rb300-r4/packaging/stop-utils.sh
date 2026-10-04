# Included in APK scripts, not installed as a separate service.
minscale_remember_service() {
    minscale_wait_pids=
    for minscale_pid in $(ubus call service list '{"name":"tailscale"}' 2>/dev/null |
        jsonfilter -e '@.tailscale.instances.*.pid' 2>/dev/null); do
        case "$minscale_pid" in ''|*[!0-9]*) continue;; esac
        minscale_ticks=$(awk '{print $22}' "/proc/$minscale_pid/stat" 2>/dev/null) || continue
        minscale_wait_pids="$minscale_wait_pids $minscale_pid:$minscale_ticks"
    done
}

minscale_wait_service() {
    for minscale_identity in $minscale_wait_pids; do
        minscale_pid=${minscale_identity%:*}
        minscale_ticks=${minscale_identity#*:}
        minscale_wait=0
        while [ "$(awk '{print $22}' "/proc/$minscale_pid/stat" 2>/dev/null)" = "$minscale_ticks" ]; do
            minscale_wait=$((minscale_wait + 1))
            if [ "$minscale_wait" -gt 20 ]; then
                echo 'MinScale: tailscaled did not finish stopping.' >&2
                return 1
            fi
            sleep 1
        done
    done
}

minscale_detach_image() {
    if grep -qs ' /usr/lib/minscale/bin squashfs ' /proc/mounts; then
        # A long-running CLI may still use the old image after the daemon exits.
        # Lazy detach preserves its existing mappings and frees the loop device
        # once the last reference closes, like an unlinked executable on upgrade.
        umount /usr/lib/minscale/bin 2>/dev/null || umount -l /usr/lib/minscale/bin
    fi
}
