# SPDX-License-Identifier: GPL-3.0-or-later
"""Instrument a private native build and execute isolated subsystem checks.

GCC's trap mode needs no libubsan runtime (official instrumentation options:
https://gcc.gnu.org/onlinedocs/gcc/Instrumentation-Options.html). A private
Windows exception observer reports the failing instruction and terminates the
test process before a desktop error dialog. It changes no production source.
"""
import argparse,hashlib,json,os,re,shutil,subprocess,time
from pathlib import Path
from native_conversion_audit import SHARED,REDUX

PROBE=r'''
#include <windows.h>
#include <stdio.h>
#include <stdint.h>
static LONG CALLBACK observe_fault(PEXCEPTION_POINTERS info) {
    uintptr_t base=(uintptr_t)GetModuleHandleW(NULL);
    uintptr_t pc=(uintptr_t)info->ExceptionRecord->ExceptionAddress;
    fprintf(stderr,"PRIVATE_SANITIZER_FAULT code=%08lx lookup=%llx rva=%llx thread=%lu\n",
      (unsigned long)info->ExceptionRecord->ExceptionCode,
      (unsigned long long)(pc-base+0x140000000ULL),
      (unsigned long long)(pc-base),(unsigned long)GetCurrentThreadId());
    fflush(stderr);
    TerminateProcess(GetCurrentProcess(),95);
    return EXCEPTION_CONTINUE_SEARCH;
}
static void __attribute__((constructor)) install_observer(void) {
    SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);
    AddVectoredExceptionHandler(1,observe_fault);
}
'''
TOY=r'''
int main(int argc,char **argv) {
    volatile int number=(argc>1 && argv[1][0]=='-') ? -1 : 1;
    volatile int output=number<<1;
    return output==2 ? 0 : 7;
}
'''
FLAGS='-fsanitize=undefined,float-cast-overflow -fsanitize-trap=all -fno-omit-frame-pointer -g'

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source','cmake','gcc','sdl','python','original-assets','redux-assets','msu-dir','scratch','output'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    for name in vars(a):
        setattr(a,name,getattr(a,name).resolve())
    for name in ('source','sdl','msu_dir'):
        if not getattr(a,name).is_dir():raise ValueError('Required directory missing: '+name)
    for name in ('cmake','gcc','python','original_assets','redux_assets'):
        if not getattr(a,name).is_file():raise ValueError('Required file missing: '+name)
    if a.scratch.exists():raise ValueError('Use fresh private scratch.')
    a.scratch=a.scratch.resolve();a.scratch.mkdir(parents=True)
    sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
    before={name:sha(getattr(a,name)) for name in ('original_assets','redux_assets','gcc')}
    def source_manifest():
        # Concurrent read-only Python QA can create bytecode caches. These
        # generated caches are not compilation/source inputs; retain all
        # actual source files in the before/after identity check.
        return {file.relative_to(a.source).as_posix():sha(file) for file in a.source.rglob('*') if file.is_file() and '.git' not in file.parts and '__pycache__' not in file.parts and file.suffix not in ('.pyc','.pyo')}
    source_before=source_manifest()
    (a.scratch/'source-input-manifest.json').write_text(json.dumps(source_before,indent=2)+'\n')
    env=dict(os.environ);env['PATH']=str(a.gcc.parent.resolve())+os.pathsep+str(a.python.parent.resolve())+os.pathsep+env['PATH']
    env.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy')
    env['PYTHONDONTWRITEBYTECODE']='1'
    def run(name,command,timeout=300):
        result=subprocess.run(list(map(str,command)),cwd=a.scratch,env=env,capture_output=True,timeout=timeout)
        (a.scratch/(name+'.log')).write_bytes(result.stdout+result.stderr)
        return result
    (a.scratch/'observer.c').write_text(PROBE,encoding='utf-8')
    (a.scratch/'negative-control.c').write_text(TOY,encoding='utf-8')
    observer=a.scratch/'observer.o';toy=a.scratch/'negative-control.exe'
    result=run('observer-compile',[a.gcc,'-g','-c',a.scratch/'observer.c','-o',observer]);assert result.returncode==0,result.stderr[-1500:]
    result=run('control-compile',[a.gcc,'-std=c11',*FLAGS.split(),a.scratch/'negative-control.c',observer,'-Wl,--image-base,0x140000000','-o',toy]);assert result.returncode==0,result.stderr[-1500:]
    positive=run('positive-control',[toy]);negative=run('negative-control',[toy,'-'])
    assert positive.returncode==0 and negative.returncode==95 and b'PRIVATE_SANITIZER_FAULT' in negative.stderr,(positive.returncode,negative.returncode,negative.stderr)
    build=a.scratch/'build'
    result=run('configure',[a.cmake,'-S',a.source.resolve()/'port/unix','-B',build,'-G','Ninja','-DCMAKE_BUILD_TYPE=RelWithDebInfo','-DEB_RUNTIME_ASSETS=ON','-DEB_ENABLE_VERIFY=OFF','-DEB_ENABLE_AUDIO=ON','-DEB_QA_OBSERVER=OFF','-DENABLE_ASAN=OFF','-DENABLE_UBSAN=OFF','-DEB_UPDATER_REPO=','-DEB_UPDATER_TOKEN=',f'-DSDL2_DIR={a.sdl.resolve().as_posix()}/lib/cmake/SDL2',f'-DPython3_EXECUTABLE={a.python.resolve().as_posix()}',f'-DCMAKE_C_FLAGS={FLAGS}',f'-DCMAKE_EXE_LINKER_FLAGS={observer.as_posix()} -Wl,--image-base,0x140000000'])
    assert result.returncode==0,result.stderr[-1500:]
    result=run('compile',[a.cmake,'--build',build,'--target','earthbound','--parallel','4'],600);assert result.returncode==0,result.stderr[-1500:]
    shutil.copy2(a.sdl/'bin/SDL2.dll',build/'SDL2.dll')
    exe=build/'earthbound.exe';rows=[]
    for mode,pack in (('original',a.original_assets),('redux',a.redux_assets)):
        for test,area in {**SHARED,**(REDUX if mode=='redux' else {})}.items():
            folder=a.scratch/(mode+'-'+test);folder.mkdir()
            command=[exe,'--assets',pack.resolve(),'--session-dir',folder,'--save',folder/'fixture.srm','--allow-redux-development','--headless','--selftest-'+test]
            if test in ('sfx-audio','bicycle-audio','redux-audio'):command+=['--msu-dir',a.msu_dir.resolve(),'--msu-name','eb_msu1']
            started=time.monotonic();result=run(mode+'-'+test,command,120);log=(result.stdout+result.stderr).decode(errors='replace')
            fault=re.search(r'PRIVATE_SANITIZER_FAULT code=([0-9a-f]+) lookup=([0-9a-f]+)',log)
            location=None
            if fault:
                addr=run(mode+'-'+test+'-location',[a.gcc.with_name('addr2line.exe'),'-e',exe,'-f','-C','0x'+fault.group(2)])
                location=addr.stdout.decode(errors='replace').strip()
            passed=result.returncode==0 and bool(re.search(r'\bPASS\b',log)) and not fault
            rows.append({'Mode':mode,'Test':test,'Area':area,'ExitCode':result.returncode,'Passed':passed,'Fault':fault.group(1) if fault else None,'Location':location,'Seconds':round(time.monotonic()-started,3),'Log':mode+'-'+test+'.log'})
            print(json.dumps(rows[-1]),flush=True)
    assert before=={name:sha(getattr(a,name)) for name in before}
    assert source_before==source_manifest()
    record={'Passed':all(row['Passed'] for row in rows),'CompilerSha256':before['gcc'],'Flags':FLAGS,'ExecutableSha256':sha(exe),'LibrarySha256':sha(build/'game_lib/libearthbound_game.a'),'SourceManifestSha256':hashlib.sha256(json.dumps(source_before,sort_keys=True).encode()).hexdigest(),'SourceManifestExcludesOnlyGitAndGeneratedPythonBytecode':True,'NegativeSignedShiftControlTrapped':True,'PositiveControlPassed':True,'RequiredCases':len(rows),'ExecutedCases':len(rows),'SkippedCases':0,'Cases':rows,'OwnerInputsAndSourceUnchanged':True,'SharedBuildChanged':False,'FullCompatibilityVerified':False,'FullPlaythroughVerified':False,'Limits':['Instrumented private rebuild executes selected existing subsystem checks, not every game path. Its compiler flags and exception observer differ from the production executable.','GCC diagnoses covered C undefined operations; absence of a trap is not proof of all memory safety, visual/audio parity or story correctness.','The Windows exception observer changes only crash reporting/termination. No game handler, postcondition or test result is replaced.']}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'Passed':record['Passed'],'Cases':len(rows),'Failures':sum(not row['Passed'] for row in rows)}),flush=True)
    if not record['Passed']:raise SystemExit(1)

if __name__=='__main__':main()
