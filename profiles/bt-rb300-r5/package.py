#!/usr/bin/env python3
"""Build a local evaluation APK. This never uploads or installs the package."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

root=Path(__file__).resolve().parent
templates=root
old=root/'package-hooks'
version='1.103.0_pre20260924-r5'
name='tailscale-lowmem'

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--variant',default='coldinline-safe-zstd-lowmem')
p.add_argument('--work',type=Path,required=True,help='empty package output directory')
p.add_argument('--artifacts',type=Path,required=True,help='directory containing tailscaled-arm64 and tailscale-arm64')
p.add_argument('--sdk-host',type=Path,required=True,help='OpenWrt SDK staging_dir/host')
p.add_argument('--sign-key',type=Path,required=True,help='private signing key; kept outside recipe')
p.add_argument('--keys-dir',type=Path,required=True,help='directory containing the matching public key')
p.add_argument('--upx',type=Path,help='verified UPX executable; required for --cli-upx')
p.add_argument('--profile-off',action='store_true')
p.add_argument('--cli-upx',action='store_true')
p.add_argument('--compact-block',type=int,choices=[64,128,256],help='store both ELFs in an XZ SquashFS image')
a=p.parse_args()
root=a.work.resolve()
root.mkdir(parents=True,exist_ok=True)
if any(root.iterdir()):p.error('--work must be empty')
host=a.sdk_host.resolve()
apk=host/'bin/apk'
a.artifacts=a.artifacts.resolve()
shutil.copytree(templates/'packaging',root/'packaging')
if a.compact_block and a.cli_upx:p.error('do not pack UPX inside the executable filesystem')
profile='compact' if a.compact_block else 'plain'
staging=root/('package-root-'+profile)
if staging.exists():raise SystemExit('package-root already exists; inspect it before rebuilding')
shutil.copytree(templates/'package-template',staging,symlinks=True)
(staging/'usr/sbin').mkdir(parents=True)
daemon=(a.artifacts/'tailscaled-arm64').resolve()
cli=(a.artifacts/'tailscale-arm64').resolve()
if a.cli_upx:
    if not a.upx:p.error('--cli-upx requires --upx')
    original=cli
    cli=root/'tailscale-packed'
    subprocess.run([str(a.upx.resolve()),'--best','--lzma','-o',str(cli),str(original)],check=True)
    subprocess.run([str(a.upx.resolve()),'-t',str(cli)],check=True)
    unpacked=root/'tailscale-roundtrip'
    subprocess.run([str(a.upx.resolve()),'-d','-o',str(unpacked),str(cli)],check=True)
    if digest(unpacked)!=digest(original):raise SystemExit('UPX round trip failed')
    unpacked.unlink()
shutil.copyfile(daemon,staging/'usr/sbin/tailscaled')
shutil.copyfile(cli,staging/'usr/sbin/tailscale')
for f in ['tailscale','tailscaled']:(staging/'usr/sbin'/f).chmod(0o755)
scripts={script:old/script for script in ['post-install','pre-deinstall','post-upgrade']}
script_dir=root/('package-scripts-'+profile)
script_dir.mkdir()
stop_utils=(root/'packaging/stop-utils.sh').read_text()
upgrade_text=(root/'packaging/compact-pre-upgrade').read_text().replace('# @STOP_UTILITIES@',stop_utils)
upgrade_script=script_dir/'pre-upgrade'
upgrade_script.write_text(upgrade_text)
scripts['pre-upgrade']=upgrade_script
image_metadata=None
if a.compact_block:
    image_source=root/'package-image-source'
    image_source.mkdir(exist_ok=False)
    for f in ['tailscale','tailscaled']:
        shutil.copyfile(staging/'usr/sbin'/f,image_source/f)
        (image_source/f).chmod(0o755)
    image_id=hashlib.sha256((digest(daemon)+digest(cli)).encode()).hexdigest()
    (image_source/'image-id').write_text(image_id+'\n')
    lib=staging/'usr/lib/minscale'
    lib.mkdir(parents=True)
    (lib/'bin').mkdir()
    (lib/'image-id').write_text(image_id+'\n')
    image=lib/'bin.squashfs'
    subprocess.run(['mksquashfs',str(image_source),str(image),'-noappend','-all-root',
                    '-comp','xz','-b',str(a.compact_block*1024),'-Xdict-size',str(a.compact_block*1024),
                    '-mkfs-time','0','-all-time','0','-processors','2','-no-progress'],check=True)
    image_metadata={'bytes':image.stat().st_size,'sha256':digest(image),'block_kib':a.compact_block,'image_id':image_id}
    for f in ['tailscale','tailscaled']:
        wrapper=staging/'usr/sbin'/f
        wrapper.write_text('#!/bin/sh\nset -e\n/usr/libexec/minscale-image ensure\nexec /usr/lib/minscale/bin/'+f+' "$@"\n')
        wrapper.chmod(0o755)
    (staging/'usr/libexec').mkdir(parents=True,exist_ok=True)
    for source,destination in [('minscale-image','usr/libexec/minscale-image'),('minscale-bin.init','etc/init.d/minscale-bin')]:
        shutil.copyfile(root/'packaging'/source,staging/destination)
        (staging/destination).chmod(0o755)
    for script_name in ['post-install','post-upgrade']:
        file=script_dir/script_name
        file.write_text((old/script_name).read_text()+'\n[ -n "${IPKG_INSTROOT:-}" ] || /etc/init.d/minscale-bin enable\n')
        scripts[script_name]=file
    file=script_dir/'pre-deinstall'
    file.write_text((old/'pre-deinstall').read_text().replace('default_prerm\n',stop_utils+
                    '\n[ -n "${IPKG_INSTROOT:-}" ] || minscale_remember_service\n'
                    'default_prerm\nresult=$?\n'
                    'if [ -z "${IPKG_INSTROOT:-}" ]; then\n'
                    '    minscale_wait_service || result=1\n'
                    '    minscale_detach_image || result=1\n'
                    'fi\nexit "$result"\n'))
    scripts['pre-deinstall']=file
    scripts['pre-install']=root/'packaging/compact-pre-install'
    file=script_dir/'pre-upgrade'
    file.write_text((root/'packaging/compact-pre-install').read_text()+'\n'+upgrade_text)
    scripts['pre-upgrade']=file
if a.profile_off:
    init=staging/'etc/init.d/tailscale'
    text=init.read_text().replace('local gogc gomemlimit','local gogc gomemlimit godebug')
    text=text.replace('  config_get gomemlimit "settings" gomemlimit 24MiB',
                      '  config_get gomemlimit "settings" gomemlimit 24MiB\n'
                      '  config_get godebug "settings" godebug memprofilerate=0')
    text=text.replace('  [ -z "$gomemlimit" ] || procd_append_param env GOMEMLIMIT="$gomemlimit"',
                      '  [ -z "$gomemlimit" ] || procd_append_param env GOMEMLIMIT="$gomemlimit"\n'
                      '  [ -z "$godebug" ] || procd_append_param env GODEBUG="$godebug"')
    init.write_text(text)
    cfg=staging/'etc/config/tailscale'
    cfg.write_text(cfg.read_text()+
                   '\t# This build omits pprof; disable allocation sampling from process startup.\n'
                   "\toption godebug 'memprofilerate=0'\n")
cfg=staging/'etc/config/tailscale'
(staging/'lib/apk/packages/tailscale-lowmem.conffiles_static').write_text('/etc/config/tailscale '+digest(cfg)+'\n')
installed_files=sorted('/'+str(path.relative_to(staging)) for path in staging.rglob('*')
                       if (path.is_file() or path.is_symlink())
                       and not str(path.relative_to(staging)).startswith('lib/apk/packages/'))
(staging/'lib/apk/packages/tailscale-lowmem.list').write_text('\n'.join(installed_files)+'\n')
subprocess.run(['sh','-n',str(staging/'etc/init.d/tailscale')],check=True)
output=root/'delivery'
output.mkdir(exist_ok=True)
package=output/(name+'-'+version+'-'+profile+'-aarch64_cortex-a53.apk')
if package.exists():raise SystemExit('refusing to overwrite an existing signed artifact')
metadata={'name':name,'version':version,
          'description':'MinScale LowMem '+profile+' local evaluation build for ARM64 OpenWrt. Preserves the LowMem r3 feature set.',
          'arch':'aarch64_cortex-a53','license':'BSD-3-Clause MIT','url':'https://tailscale.com',
          'origin':'minscale-stage5','depends':'ca-bundle kmod-tun libc',
          'provides':'tailscale-lowmem-any tailscaled='+version}
if a.compact_block:metadata['depends']+=' kmod-loop kmod-fs-squashfs'
cmd=[str(host/'bin/fakeroot'),str(apk),'mkpkg']
for k,v in metadata.items():cmd+=['--info',k+':'+v]
for script,path in scripts.items():
    subprocess.run(['sh','-n',str(path)],check=True)
    cmd+=['--script',script+':'+str(path)]
cmd+=['--files',str(staging),'--sign-key',str(a.sign_key.resolve()),
      '--output',str(package)]
subprocess.run(cmd,env=dict(os.environ,STAGING_DIR_HOST=str(host)),check=True)
subprocess.run([str(apk),'--keys-dir',str(a.keys_dir.resolve()),'verify',str(package)],check=True)
manifest={'status':'local evaluation; target package lifecycle and soak must be checked separately',
          'package':package.name,'package_bytes':package.stat().st_size,'package_sha256':digest(package),
          'variant':a.variant,'profile':profile,'profile_off':a.profile_off,'cli_upx':a.cli_upx,
          'daemon_sha256':digest(daemon),'cli_sha256':digest(cli),
          'daemon_bytes':daemon.stat().st_size,'cli_bytes':cli.stat().st_size,
          'logical_executable_bytes':daemon.stat().st_size+cli.stat().st_size,
          'metadata':metadata,'image':image_metadata}
(output/('manifest-'+profile+'.json')).write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(manifest,indent=2))
