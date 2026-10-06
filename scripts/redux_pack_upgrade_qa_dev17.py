# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise the real owner-ROM Redux upgrade using isolated copies only.

Source and current packs, phone/F6 saves and owner ROM are read-only inputs.
This tests setup, guarded migration and seed identity; natural playthroughs
and every possible serialized scene remain separately unverified.
"""
import argparse,hashlib,json,os,shutil,subprocess
from pathlib import Path
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
OLD='ed299183d4b1aff4b38c56ef16da28a256c3a65d33ba1d9327c9b19df0272ef3'
NEW='3ed273eaedad5131a13dc07b6916377130857929854886b139b30a723482f8b9'

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('launcher','native-exe','sdl','original-helper','redux-helper','original-pack','previous-pack','current-pack','rom','phone','checkpoint','scratch','output'):
  p.add_argument('--'+name,type=Path,required=True)
 a=p.parse_args()
 for name in vars(a):setattr(a,name,getattr(a,name).resolve())
 if a.scratch.exists():raise ValueError('Fresh private scratch required')
 sources={str(getattr(a,n)):sha(getattr(a,n))for n in vars(a)if n not in ('scratch','output')}
 if sha(a.previous_pack)!=OLD or sha(a.current_pack)!=NEW:raise ValueError('Reviewed previous/current packs required')
 a.scratch.mkdir(parents=True);app=a.scratch/'app';game=app/'Game';profile=app/'Profiles/maternalbound-redux-897d0083';user=app/'UserData'
 for path in(game,profile,user):path.mkdir(parents=True,exist_ok=True)
 for src,dest in((a.launcher,app/'EarthBound Companion.exe'),(a.native_exe,game/'earthbound.exe'),(a.sdl,game/'SDL2.dll'),(a.original_helper,game/'ebtools-setup.exe'),(a.redux_helper,game/'redux-setup.exe'),(a.original_pack,game/'assets.pak'),(a.previous_pack,profile/'assets.pak')):shutil.copy2(src,dest)
 (profile/'profile.json').write_text(json.dumps({'contentId':'maternalbound-redux-897d0083','assetPackSha256':OLD}))
 settings={'AssetPack':str(profile/'assets.pak'),'ReduxDevelopmentEnabled':True,'HqAudio':False,'Fullscreen':False}
 (user/'settings.json').write_text(json.dumps(settings))
 saves=user/'ContentProfiles'/OLD/'Game/saves';saves.mkdir(parents=True)
 shutil.copy2(a.phone,saves/'earthbound.srm')
 for name in ('quicksave_1.bin.0','quicksave_1.bin.1'):shutil.copy2(a.checkpoint,saves/name)
 save_before={f.name:sha(f)for f in saves.iterdir()};checks=[]
 env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy');env.pop('PYTHONHOME',None);env.pop('PYTHONPATH',None)
 def run(name,args,timeout=300):
  result=subprocess.run([str(app/'EarthBound Companion.exe'),'--data-root',str(app),*map(str,args)],cwd=app,env=env,capture_output=True,timeout=timeout)
  (a.scratch/(name+'.log')).write_bytes(result.stdout+result.stderr)
  if result.returncode:raise RuntimeError(name+': '+(result.stdout+result.stderr).decode(errors='replace')[-2500:])
 def require(value,reason):
  if not value:raise ValueError(reason)
  checks.append(reason)
 run('old-seed',['--generate-seed','Legacy upgrade preservation'])
 seeds_before={f.relative_to(user/'Seeds').as_posix():sha(f)for f in(user/'Seeds').rglob('*')if f.is_file()}
 run('actual-upgrade',['--setup-redux',a.rom])
 require(sha(profile/'assets.pak')==NEW,'Real owner-ROM helper produces exact corrected pack')
 backups=list((app/'Profiles').glob('maternalbound-redux-897d0083-backup-'+OLD[:8]+'-*'))
 require(len(backups)==1 and sha(backups[0]/'assets.pak')==OLD,'Previous profile backed up with unchanged asset bytes')
 require(save_before=={f.name:sha(f)for f in saves.iterdir()},'Previous phone and both F6 files unchanged')
 current=user/'ContentProfiles'/NEW/'Game/saves'
 require(save_before=={f.name:sha(f)for f in current.iterdir()},'New story namespace contains exact copied saves')
 seeds_after={f.relative_to(user/'Seeds').as_posix():sha(f)for f in(user/'Seeds').rglob('*')if f.is_file()}
 require(all(seeds_after.get(path)==digest for path,digest in seeds_before.items()),'Every pre-existing seed data, recipe and save file unchanged')
 added_seed_files=sorted(set(seeds_after)-set(seeds_before))
 # Updating Original's movement-bank data can also create the documented
 # starter seed. An additional seed is not a mutation of an existing run.
 added_folders={path.split('/')[0]for path in added_seed_files}
 require(len(added_folders)<=1 and all(json.loads((user/'Seeds'/folder/'seed.json').read_text())['Seed']=='Tonight in Onett' and json.loads((user/'Seeds'/folder/'seed.json').read_text())['BaseHash']==OLD for folder in added_folders),'Any added seed is only the documented starter on the retained old base')
 settings=json.loads((user/'settings.json').read_text());require(Path(settings['AssetPack']).resolve()==profile/'assets.pak','Setup selects corrected story profile')
 settings['AssetPack']=str(backups[0]/'assets.pak');(user/'settings.json').write_text(json.dumps(settings))
 legacy_seed=next(path.parent for path in(user/'Seeds').glob('*/seed.json')if json.loads(path.read_text())['Seed']=='Legacy upgrade preservation');run('verify-legacy-seed',['--check-seed',legacy_seed])
 for folder in added_folders:run('verify-starter-'+folder[:8],['--check-seed',user/'Seeds'/folder])
 require(json.loads((legacy_seed/'seed.json').read_text())['BaseHash']==OLD,'Legacy seed verifies with its retained original base')
 settings['AssetPack']=str(profile/'assets.pak');(user/'settings.json').write_text(json.dumps(settings))
 run('new-seed',['--generate-seed','Corrected art seed'])
 new_seed=next(p.parent for p in(user/'Seeds').glob('*/seed.json')if json.loads(p.read_text())['BaseHash']==NEW)
 run('verify-new-seed',['--check-seed',new_seed]);checks.append('New seed generates and passes independent content guard on corrected base')
 run('owner-checkpoint',['--checkpoint-recovery-test',profile/'assets.pak',a.checkpoint,a.scratch/'checkpoint-recovery'])
 require(json.loads((a.scratch/'checkpoint-recovery/results.json').read_text())['Passed'],'Actual copied owner F6 backup/restore/native load passes')
 before_repeat={str(f.relative_to(app)):sha(f)for directory in(profile,user/'ContentProfiles')for f in directory.rglob('*')if f.is_file()}
 run('repeat-setup',['--setup-redux',a.rom])
 require(before_repeat=={str(f.relative_to(app)):sha(f)for directory in(profile,user/'ContentProfiles')for f in directory.rglob('*')if f.is_file()},'Repeated current setup leaves profile and saves unchanged')
 require(not list((app/'Profiles').rglob('*.sfc')) and not list((app/'Profiles').rglob('*.smc')),'Successful setup retains no generated ROM')
 require(sources=={path:sha(path)for path in sources},'All supplied owner/source inputs unchanged')
 report={'Passed':True,'Checks':checks,'Inputs':sources,'PreviousPackSha256':OLD,'CurrentPackSha256':NEW,'CopiedSaveSha256':save_before,'PreviousSeedFiles':seeds_before,'AddedStarterSeedFiles':added_seed_files,'SourceAndOwnerFilesModified':False,'FullPlaythroughVerified':False,'ToolSha256':sha(__file__),'Limits':['Real setup/import/generation and cold checkpoint load on isolated copies, not complete story or seed progression.','Legacy seeds require selecting their retained base pack; they are never relabeled to new graphics.','An imported mid-battle checkpoint retains cached art until the next battle loads; separate prepared-scene proof covers that behavior.']}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'Passed':True,'Checks':len(checks)}))
if __name__=='__main__':main()
