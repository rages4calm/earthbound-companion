# SPDX-License-Identifier: GPL-3.0-or-later
"""Execute existing real-mode scenarios against a private instrumented library.

Only the test-driver builder is substituted. Scenario inputs, production mode
dispatch, children and assertions remain the selected tool's actual code. The
instrumented library is not a shipping/independent-reference runtime.
"""
import argparse,hashlib,importlib,json,os,re,shutil,subprocess,sys,time
from pathlib import Path

ALLOWED={'redux_story_cutscene_parent_qa','timed_item_lifecycle_qa',
 'timed_item_cold_continue_qa','battle_full_encounter_qa_dev18',
 'battle_ko_lifecycle_qa_dev17','inventory_gameover_lifecycle_qa_dev17',
 'redux_prayer_cinematic_qa','redux_ending_transaction_qa'}
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--tool',choices=sorted(ALLOWED),required=True)
 p.add_argument('--sanitizer-root',type=Path,required=True)
 p.add_argument('--door-o0-diagnostic',action='store_true',help='Compile the exact same door.c at O0 for precise trap source locations, privately.')
 p.add_argument('arguments',nargs=argparse.REMAINDER)
 own=p.parse_args();san=own.sanitizer_root.resolve();build=san/'build'
 if not (san/'negative-control.log').is_file() or 'PRIVATE_SANITIZER_FAULT' not in (san/'negative-control.log').read_text():raise ValueError('Actual negative-control trap required')
 if not (san/'positive-control.log').is_file():raise ValueError('Positive control required')
 original={str(path):sha(path)for path in (build/'earthbound.exe',build/'game_lib/libearthbound_game.a',san/'observer.o')}
 commands=json.loads((build/'compile_commands.json').read_text())
 entry=next(x for x in commands if x['file'].replace('\\','/').endswith('/port/unix/main.c'))
 if '"' in entry['command'] or "'" in entry['command']:raise ValueError('Review quoted compiler flags')
 flags=entry['command'].split();compiler=Path(flags[0]);os.environ['PATH']=str(compiler.parent)+os.pathsep+os.environ['PATH']
 ninja=(build/'build.ninja').read_text()
 match=re.search(r'^build earthbound.exe: C_EXECUTABLE_LINKER__earthbound_\w+ (.*?)\n(.*?)(?=\n\n)',ninja,re.M|re.S)
 if not match:raise ValueError('Unknown player link rule')
 tokens=match[1].split(' | ',1)[0].split();libraries=re.search(r'^  LINK_LIBRARIES = (.*)$',match[2],re.M)[1].split()
 linkflags=re.search(r'^  LINK_FLAGS = (.*)$',match[2],re.M)[1].split()
 if str(san/'observer.o').replace('\\','/') not in ' '.join(linkflags).replace('\\','/'):raise ValueError('Exception observer must be linked')
 def private(a,out,driver,wrap=False):
  out=Path(out).resolve()
  if a.build.resolve()!=build:raise ValueError('Scenario must use exact instrumented build')
  if getattr(a,'corrected_callback_source',None):raise ValueError('Production replacements forbidden')
  source=out/'instrumented-scenario.c';source.write_text(driver,encoding='utf-8');obj=out/'instrumented-scenario.o'
  cflags=flags.copy();cflags[cflags.index('-c')+1]=str(source);cflags[cflags.index('-o')+1]=str(obj)
  def run(command,name):
   r=subprocess.run(list(map(str,command)),cwd=build,capture_output=True,timeout=120)
   (out/name).write_bytes(r.stdout+r.stderr)
   if r.returncode:raise RuntimeError(name+': '+r.stderr.decode(errors='replace'))
  run(cflags,'instrumented-driver-compile.log')
  main=next(x for x in tokens if x.replace('\\','/').endswith('/main.c.obj'))
  copied=out/'instrumented-main.o';shutil.copy2(build/main,copied)
  run([compiler.parent/'objcopy.exe','--redefine-sym','main=eb_platform_main',copied],'instrumented-main-rename.log')
  objects=[copied if x==main else build/x for x in tokens];exe=out/'instrumented-scenario.exe';libs=libraries.copy()
  linked_library=build/'game_lib/libearthbound_game.a'
  diagnostic_source=None
  if own.door_o0_diagnostic:
   centry=next(x for x in commands if x['file'].replace('\\','/').endswith('/game/door.c'))
   if '"'in centry['command']or "'"in centry['command']:raise ValueError('Review quoted door flags')
   cflags=centry['command'].split();cflags=[('-O0'if v=='-O2'else v)for v in cflags];cobj=out/'door.c.obj';cflags[cflags.index('-o')+1]=str(cobj)
   run(cflags,'instrumented-door-o0.log');lib=out/'diagnostic-game.a';shutil.copy2(build/'game_lib/libearthbound_game.a',lib)
   run([compiler.parent/'ar.exe','r',lib,cobj],'instrumented-door-archive.log')
   indices=[i for i,v in enumerate(libs)if v.replace('\\','/').endswith('game_lib/libearthbound_game.a')]
   if len(indices)!=1:raise ValueError('Unknown archive link layout')
   libs[indices[0]]=str(lib)
   linked_library=lib;diagnostic_source=Path(centry['file'])
  run([compiler,obj,*objects,'-o',exe,*linkflags,*(['-Wl,--wrap=call_move_callback']if wrap else []),*libs],'instrumented-driver-link.log')
  shutil.copy2(build/'SDL2.dll',out/'SDL2.dll')
  return exe,{'driverSourceSha256':sha(source),'DriverSourceSha256':sha(source),'ExecutableSha256':sha(exe),'executableSha256':sha(exe),'InstrumentedLibrarySha256':sha(build/'game_lib/libearthbound_game.a'),'LinkedLibrarySha256':sha(linked_library),'DoorDiagnosticSourceSha256':sha(diagnostic_source)if diagnostic_source else None,'InstrumentedPlatformMainSha256':sha(build/main),'InstrumentedPlayerSha256':sha(build/'earthbound.exe'),'SharedBuildModified':False,'sharedBuildModified':False,'SharedSourceModified':False,'sharedSourceModified':False,'UntouchedInstrumentedLibraryLinked':not own.door_o0_diagnostic,'ReadOnlyPrePostCallbackWrapper':wrap,'Method':('Private GCC trap-instrumented rebuild; exact door.c privately recompiled at O0 and replaced in a copied archive for source-location diagnosis. Other production objects retained, copied main symbol renamed.' if own.door_o0_diagnostic else 'Private GCC trap-instrumented rebuild; production objects retained, copied main symbol renamed.')+' No scenario result or game handler replaced.','NegativeSignedShiftControlTrapped':True,'Limits':['Diagnostic compiler flags and exception observer differ from shipping code. No independent SNES-reference or shipping-runtime proof is claimed.']}
 import battle_action_catalog_qa as battle
 import party_follow_private_build as party
 battle.private_build=lambda a:private(a,a.scratch,battle.DRIVER)
 party.private_build=private
 target=importlib.import_module(own.tool)
 arguments=own.arguments[1:]if own.arguments and own.arguments[0]=='--'else own.arguments
 sys.argv=[own.tool+'.py',*arguments]
 failure=None
 try:target.main()
 except (Exception,SystemExit) as error:
  failure={'Type':type(error).__name__,'Message':str(error)}
 finally:
  unchanged=original=={path:sha(Path(path))for path in original}
  if not unchanged:raise RuntimeError('Instrumented inputs changed')
 scratch=Path(arguments[arguments.index('--scratch')+1]).resolve()
 output=Path(arguments[arguments.index('--output')+1]).resolve()
 faults=[]
 for log in scratch.rglob('*.log'):
  for code,lookup in re.findall(r'PRIVATE_SANITIZER_FAULT code=([0-9a-f]+) lookup=([0-9a-f]+)',log.read_text(errors='replace')):
   location=subprocess.run([str(compiler.parent/'addr2line.exe'),'-e',str(scratch/'instrumented-scenario.exe'),'-f','-C','-i','0x'+lookup],capture_output=True).stdout.decode(errors='replace').strip()
   faults.append({'Log':log.relative_to(scratch).as_posix(),'ExceptionCode':code,'LookupAddress':lookup,'Location':location,'LogSha256':sha(log)})
 record={'Passed':failure is None and not faults,'Tool':own.tool,'ScenarioToolSha256':sha(Path(target.__file__)),'BuilderToolSha256':sha(Path(__file__)),'InstrumentedInputs':original,'DoorSourcePrivatelyRecompiledAtO0':own.door_o0_diagnostic,'DiagnosticBuildSource':str(build),'Faults':faults,'RunnerFailure':failure,'InputsUnchanged':unchanged,'ScenarioReportExists':output.is_file(),'Limits':['Only the driver builder is substituted; inputs, production dispatch and assertions remain the selected existing tool.','Instrumentation and crash reporting differ from shipping code. Traps identify diagnostic failures, not an observed production crash or independent game parity.','If a scenario traps before a cold checkpoint exists, its original runner can stop before later cases; no skipped case is counted as passed.']}
 if output.is_file():record['ScenarioReportSha256']=sha(output)
 output.parent.mkdir(parents=True,exist_ok=True);output.with_suffix('.diagnostic.json').write_text(json.dumps(record,indent=2)+'\n')
 if not record['Passed']:raise SystemExit(1)

if __name__=='__main__':main()
