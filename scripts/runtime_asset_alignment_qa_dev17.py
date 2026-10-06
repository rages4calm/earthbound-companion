# SPDX-License-Identifier: GPL-3.0-or-later
"""Validate real pack bytes, host alignment, failed loads and repeat/unload.

Uses real loader/layout source, selected local packs and private shifted packs.
All payloads remain private. Expected bytes come independently from EBPK indices.
"""
import argparse,hashlib,json,os,re,struct,subprocess
from pathlib import Path
from native_sanitizer_qa_dev17 import PROBE,FLAGS
DRIVER=r'''
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "data/runtime_assets.h"
#include "data/assets.h"
#include "asset_pack_layout.h"
static uint32_t u32(const unsigned char*p){return p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static uint16_t u16(const unsigned char*p){return p[0]|((uint16_t)p[1]<<8);}
typedef struct {uint16_t x,y;uint8_t dir,transition;uint16_t extra;} TableRecord;
void *__real_malloc(size_t);void __real_free(void*);
static unsigned control,calls,fail_at,live,allocationFailures,partialFailures;
static void*owned[ASSET_COUNT];
void *__wrap_malloc(size_t n){
 if(control&&++calls==fail_at)return NULL;
 void*p=__real_malloc(n);if(control&&p){for(unsigned i=0;i<ASSET_COUNT;i++)if(!owned[i]){owned[i]=p;live++;break;}}return p;
}
void __wrap_free(void*p){if(p)for(unsigned i=0;i<ASSET_COUNT;i++)if(owned[i]==p){owned[i]=NULL;live--;break;}__real_free(p);}
int main(int argc,char**argv){
 if(argc!=3)return 2;unsigned cycles=strtoul(argv[2],0,10);FILE*f=fopen(argv[1],"rb");if(!f)return 3;
 fseek(f,0,SEEK_END);long n=ftell(f);rewind(f);unsigned char*raw=malloc(n);if(!raw||fread(raw,1,n,f)!=(size_t)n)return 4;fclose(f);
 unsigned count=u32(raw+8),start=44+count*8,assertions=0,unaligned=0,byteFailures=0,typedFailures=0,clearingFailures=0;
 for(unsigned cycle=0;cycle<cycles;cycle++){
  control=1;calls=fail_at=0;
  if(eb_runtime_assets_load(argv[1])!=EB_ASSETS_OK||!eb_runtime_assets_ready())return 5;
  unsigned allocations=calls;
  for(unsigned i=0;i<count;i++){
   unsigned off=u32(raw+44+i*8),len=u32(raw+48+i*8);const unsigned char*p=ASSET_DATA(i);
   assertions+=3;
   if(ASSET_SIZE(i)!=len||(!len&&p)|| (len&&(!p||memcmp(p,raw+start+off,len))))byteFailures++;
   if(len&&(uintptr_t)p%_Alignof(max_align_t))unaligned++;
  }
  const unsigned char*t=ASSET_DATA(ASSET_DATA_TELEPORT_DESTINATION_TABLE_BIN);unsigned len=ASSET_SIZE(ASSET_DATA_TELEPORT_DESTINATION_TABLE_BIN);
  if(t&&len%8==0){
   if((uintptr_t)t%_Alignof(TableRecord))typedFailures++;
   else for(unsigned k=0;k<len/8;k++){
    const TableRecord*r=(const TableRecord*)(t+k*8);const unsigned char*b=t+k*8;assertions+=5;
    if(r->x!=u16(b)||r->y!=u16(b+2)||r->dir!=b[4]||r->transition!=b[5]||r->extra!=u16(b+6))typedFailures++;
   }
  }
  eb_runtime_assets_unload();assertions+=2;
  if(live)allocationFailures++;
  if(eb_runtime_assets_ready())clearingFailures++;
  for(unsigned i=0;i<count;i++){assertions+=2;if(ASSET_DATA(i)||ASSET_SIZE(i))clearingFailures++;}
  if(asset_family_audiopacks[0].data||*asset_family_audiopacks[0].size_ptr||asset_family_maps_gfx[0].data||*asset_family_maps_gfx[0].size_ptr)clearingFailures++;
  /* Fail actual aligned-copy allocations at first, second and last calls. */
  unsigned targets[]={1,2,allocations};
  for(unsigned k=0;k<3;k++)if(targets[k]&&targets[k]<=allocations){
   calls=0;fail_at=targets[k];EbAssetLoadResult result=eb_runtime_assets_load(argv[1]);assertions+=3;
   if(result!=EB_ASSETS_IO_ERROR||live||eb_runtime_assets_ready())allocationFailures++;
   for(unsigned i=0;i<count;i++)if(ASSET_DATA(i)||ASSET_SIZE(i))allocationFailures++;
  }
  fail_at=0;control=0;
 }
 /* A rejected load must clear a previous successful mapping and copies. */
 control=1;calls=fail_at=0;
 if(eb_runtime_assets_load(argv[1])!=EB_ASSETS_OK)return 9;
 if(eb_runtime_assets_load("__missing_alignment_fixture__.pak")!=EB_ASSETS_MISSING||eb_runtime_assets_ready())return 10;
 for(unsigned i=0;i<count;i++)if(ASSET_DATA(i)||ASSET_SIZE(i))return 11;
 if(live)allocationFailures++;
 /* Corrupt a later nonempty index only after many earlier entries loaded. */
 char corrupt[2048];snprintf(corrupt,sizeof(corrupt),"%s.late-index.pak",argv[1]);
 unsigned last=count-1;while(last&&u32(raw+48+last*8)==0)last--;memset(raw+48+last*8,0xff,4);
 f=fopen(corrupt,"wb");if(!f||fwrite(raw,1,n,f)!=(size_t)n)return 13;fclose(f);calls=fail_at=0;
 if(eb_runtime_assets_load(corrupt)!=EB_ASSETS_IO_ERROR||live||eb_runtime_assets_ready())partialFailures++;
 for(unsigned i=0;i<count;i++)if(ASSET_DATA(i)||ASSET_SIZE(i))partialFailures++;
 remove(corrupt);control=0;
 printf("ASSET_QA {\"Assets\":%u,\"Cycles\":%u,\"Assertions\":%u,\"Alignment\":%u,\"Unaligned\":%u,\"ByteFailures\":%u,\"TypedFailures\":%u,\"ClearingFailures\":%u,\"AllocationFailures\":%u,\"PartialLoadCleanupFailures\":%u}\n",count,cycles,assertions,(unsigned)_Alignof(max_align_t),unaligned,byteFailures,typedFailures,clearingFailures,allocationFailures,partialFailures);
 free(raw);return unaligned||byteFailures||typedFailures||clearingFailures||allocationFailures||partialFailures?12:0;
}
'''
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('source','gcc','original-assets','redux-assets','scratch','output'):p.add_argument('--'+name,type=Path,required=True)
 p.add_argument('--diagnostic',action='store_true');a=p.parse_args()
 for n,v in vars(a).copy().items():
  if isinstance(v,Path):setattr(a,n,v.resolve())
 if a.scratch.exists()or a.output.exists():raise ValueError('Fresh private output required')
 a.scratch.mkdir(parents=True);(a.scratch/'driver.c').write_text(DRIVER);(a.scratch/'observer.c').write_text(PROBE)
 inputs={str(x):sha(x)for x in (a.original_assets,a.redux_assets,a.source/'src/data/runtime_assets.c',a.source/'src/data/runtime_assets.h',a.source/'src/data/runtime_generated/asset_pack_layout.c')}
 env=dict(os.environ);env['PATH']=str(a.gcc.parent)+os.pathsep+env['PATH']
 exe=a.scratch/'asset-alignment.exe'
 command=[a.gcc,*FLAGS.split(),'-std=c11','-DEB_RUNTIME_ASSETS=1','-I'+str(a.source/'src'),'-I'+str(a.source/'src/data/runtime_generated'),a.scratch/'driver.c',a.scratch/'observer.c',a.source/'src/data/runtime_assets.c',a.source/'src/data/runtime_generated/asset_pack_layout.c','-Wl,--image-base,0x140000000','-Wl,--wrap=malloc,--wrap=free','-o',exe]
 r=subprocess.run(list(map(str,command)),env=env,capture_output=True);(a.scratch/'compile.log').write_bytes(r.stdout+r.stderr)
 if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace'))
 rows=[]
 for mode,pack in (('Original',a.original_assets),('Redux',a.redux_assets)):
  raw=pack.read_bytes();count=struct.unpack_from('<I',raw,8)[0];start=44+count*8
  for shift in range(17):
   path=pack
   if shift:
    index=bytearray(raw[44:start])
    for i in range(count):off=struct.unpack_from('<I',index,i*8)[0];struct.pack_into('<I',index,i*8,off+shift)
    path=a.scratch/(mode+'-shift-'+str(shift)+'.pak');path.write_bytes(raw[:44]+index+bytes(shift)+raw[start:])
   else:
    path=a.scratch/(mode+'-unchanged.pak');path.write_bytes(raw)
   r=subprocess.run([str(exe),str(path),'3'],cwd=a.scratch,env=env,capture_output=True,timeout=30)
   log=r.stdout+r.stderr;(a.scratch/(mode+'-'+str(shift)+'.log')).write_bytes(log)
   records=[json.loads(x[9:])for x in r.stdout.decode(errors='replace').splitlines()if x.startswith('ASSET_QA ')]
   passed=r.returncode==0 and len(records)==1
   rows.append({'Mode':mode,'PrivateBlobPrefixShift':shift,'ExitCode':r.returncode,'Passed':passed,'Measurement':records[0]if records else None,'FixturePackSha256':sha(path),'LogSha256':hashlib.sha256(log).hexdigest()})
   print(json.dumps(rows[-1]),flush=True)
 if inputs!={path:sha(path)for path in inputs}:raise RuntimeError('Read-only inputs changed')
 report={'Passed':all(x['Passed']for x in rows),'Cases':rows,'InputIdentities':inputs,'ExecutableSha256':sha(exe),'ToolSha256':sha(Path(__file__)),'Flags':FLAGS,'PrivateShiftedPackPayloadBytesUnchanged':True,'OwnerInputsUnchanged':True,'SkippedCases':0,'Limits':['Real loader/layout sources and all input asset bytes; three load/unload cycles and rejected reload per pack/shift, first/second/last allocation failure and late corrupt-index cleanup controls. No owner save writes or pack rewrite.','34 selected pack/shift cases overlap repeated asset byte assertions; no full-game or all malformed pack input claim.','Typed record comparison uses the actual eight-byte teleport table layout. Game semantics are validated separately.']}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n')
 if not report['Passed']and not a.diagnostic:raise SystemExit(1)
if __name__=='__main__':main()
