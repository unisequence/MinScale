#!/usr/bin/env python3
"""Rebuild the selected ARM64 profile without a router or historical APK.

Network access downloads the pinned upstream source, Go toolchain and modules.
No package is installed, signed, uploaded or published by this script.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent
INPUTS = json.loads((ROOT / 'inputs.json').read_text())


def run(args, cwd, **kw):
    return subprocess.run([str(x) for x in args], cwd=cwd, check=True, **kw)


def output(args, cwd):
    return run(args, cwd, capture_output=True, text=True).stdout.strip()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, required=True,
                        help='new empty directory for pinned source and build products')
    parser.add_argument('--jobs', type=int, default=4)
    parser.add_argument('--test', action='store_true', help='run selected host package tests')
    args = parser.parse_args()
    work = args.work.resolve()
    work.mkdir(parents=True, exist_ok=True)
    if any(work.iterdir()):
        parser.error('--work must be empty; this script never resets an existing checkout')
    source = work / 'source'
    source.mkdir()
    run(['git', 'init', '-q'], source)
    run(['git', 'remote', 'add', 'origin', INPUTS['upstream_repository']], source)
    # Go 1.27 derives the main-module pseudo-version from reachable release
    # tags. A one-commit clone builds, but stamps a different module version.
    run(['git', 'fetch', '--depth=1000', 'origin', INPUTS['base_commit'],
         'refs/tags/' + INPUTS['version_tag'] + ':refs/tags/' + INPUTS['version_tag']], source)
    assert output(['git', 'rev-parse', INPUTS['version_tag'] + '^{commit}'], source) == INPUTS['version_tag_commit']
    run(['git', 'bundle', 'verify', ROOT / 'patches/tailscale-profile.bundle'], source)
    run(['git', 'fetch', ROOT / 'patches/tailscale-profile.bundle',
         'HEAD:refs/heads/minscale-profile'], source)
    run(['git', 'checkout', '--detach', INPUTS['profile_commit']], source)
    assert output(['git', 'rev-parse', 'HEAD'], source) == INPUTS['profile_commit']
    assert (source / 'go.toolchain.rev').read_text().strip() == INPUTS['go_toolchain_rev']
    go = source / 'tool/go'
    toolchain = output([go, 'version'], source)
    assert toolchain == INPUTS['toolchain'], (toolchain, INPUTS['toolchain'])
    modules = json.loads(output([go, 'mod', 'download', '-json',
                         INPUTS['wireguard_module'] + '@' + INPUTS['wireguard_version']], source))
    wg = work / 'wireguard-go'
    shutil.copytree(modules['Dir'], wg)
    for path in [wg, *wg.rglob('*')]:
        path.chmod(path.stat().st_mode | 0o200)
    for patch in ('wireguard-go-gro.patch', 'wireguard-go-release.patch'):
        with (ROOT / 'patches' / patch).open('rb') as stream:
            run(['patch', '--batch', '--fuzz=0', '-p1'], wg, stdin=stream)
    artifacts = work / 'artifacts'
    artifacts.mkdir()
    modfile = artifacts / 'lowmem.mod'
    shutil.copyfile(source / 'go.mod', modfile)
    shutil.copyfile(source / 'go.sum', artifacts / 'lowmem.sum')
    run([go, 'mod', 'edit', '-modfile=' + str(modfile),
         '-replace=' + INPUTS['wireguard_module'] + '=' + str(wg)], source)
    overlay_root = work / 'overlay'
    relative = Path('control/controlclient/direct.go')
    overlay_file = overlay_root / relative
    overlay_file.parent.mkdir(parents=True)
    shutil.copyfile(source / relative, overlay_file)
    with (ROOT / 'patches/control-zstd-lowmem.patch').open('rb') as stream:
        run(['patch', '--batch', '--fuzz=0', '-p1'], overlay_root, stdin=stream)
    overlay = artifacts / 'overlay.json'
    overlay.write_text(json.dumps({'Replace': {str(source / relative): str(overlay_file)}}))
    env = dict(os.environ, CGO_ENABLED='0', GOOS='linux', GOARCH='arm64', GOARM64='v8.0')
    for key in ('GOFLAGS', 'GOEXPERIMENT', 'GOROOT'):
        env.pop(key, None)
    common = ['-p', str(args.jobs), '-modfile=' + str(modfile), '-trimpath', '-ldflags=-s -w']
    records = []
    for target, tags_file, flags, expected in [
        ('tailscaled', 'r3-feature-tags.json',
         INPUTS['gcflags'] + ['-overlay=' + str(overlay)], INPUTS['daemon_sha256']),
        ('tailscale', 'r3-cli-feature-tags.json', [], INPUTS['cli_sha256']),
    ]:
        tags = json.loads((ROOT / tags_file).read_text())
        binary = artifacts / (target + '-arm64')
        command = [go, 'build', *common, '-tags=' + ','.join(tags), *flags,
                   '-o', binary, './cmd/' + target]
        run(command, source, env=env)
        record = {'target': target, 'bytes': binary.stat().st_size,
                  'sha256': sha(binary), 'matches_measured_build': sha(binary) == expected,
                  'command': list(map(str, command)),
                  'build_info': output([go, 'version', '-m', binary], source)}
        records.append(record)
        print(target, record['bytes'], record['sha256'],
              'matches measured build:', record['matches_measured_build'], flush=True)
    assert not output(['git', 'status', '--porcelain'], source)
    if args.test:
        test_env = dict(env)
        for key in ('GOOS', 'GOARCH', 'GOARM64'):
            test_env.pop(key, None)
        tags = json.loads((ROOT / 'r3-feature-tags.json').read_text())
        run([go, 'test', '-p', str(args.jobs), '-modfile=' + str(modfile),
             '-tags=' + ','.join(tags), *INPUTS['gcflags'], '-overlay=' + str(overlay),
             './net/tstun', './net/dns', './wgengine/magicsock', './ipn/localapi',
             './control/controlclient', './tailcfg', './util/zstdframe'], source, env=test_env)
    (artifacts / 'build-results.json').write_text(json.dumps(records, indent=2) + '\n')
    if not all(r['matches_measured_build'] for r in records):
        print('Hash differences are recorded, not hidden. The daemon embeds the absolute '
              'WireGuard module replacement path in Go build information. A different '
              'work directory therefore need not reproduce the original bytes. '
              'These newly built artifacts need their own target validation.')


if __name__ == '__main__':
    main()
