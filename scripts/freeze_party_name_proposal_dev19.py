# SPDX-License-Identifier: GPL-3.0-or-later
"""Freeze a private three-file party-name proposal and independent QA evidence.

Explicit local ROM/pack inputs are read only. Outputs contain code diffs,
addresses, hashes, metadata and generated test names, never game assets/ROMs.
"""
import argparse,difflib,hashlib,json,re,struct
from pathlib import Path
from build_maternalbound_pack import read_pack
from audit_redux_remaining_features import naming_matrices
ROOT=Path(__file__).resolve().parents[1]
PIN='897d00833f4a08a0a92f106abf631629a6a6a041'
FILES=('src/game/battle.c','src/game/display_text.c','src/game/window.c')
REPORTS=('research/party-name-dev19-v2-red-r3-review.json','research/party-name-dev19-private-v1-green-review.json','research/party-name-dev19-services-v2-red-r3-review.json','research/party-name-dev19-services-private-v1-green-review.json','research/party-name-controls-dev19-v2-red-r2-review.json','research/party-name-controls-dev19-private-v2-green-review.json','research/party-name-dev19-private-build-review.json')
TOOLS=('tools/party_name_parents_qa_dev19.py','tools/party_name_label_controls_dev19.py','tools/freeze_party_name_proposal_dev19.py','tools/goods_equipment_qa_dev25.py','tools/goods_equipment_cases_dev25.py','tools/overworld_use_qa_dev24.py','tools/overworld_use_cases_dev24.py','tools/status_service_qa_dev23.py','tools/status_service_cases_dev23.py','tools/barter_delivery_qa_dev20.py','tools/transaction_menu_replay_dev20.py','tools/shop_transaction_qa_dev18.py','tools/battle_action_catalog_qa.py','tools/build_maternalbound_pack.py','tools/redux_naming_qa.py','tools/audit_redux_remaining_features.py','tools/build_title_private_dev18.py')
ASMS=('asm/text/character_select_prompt.asm','asm/text/party_character_selector.asm','asm/text/get_party_character_name.asm','asm/text/menu/add_menu_option.asm','asm/text/print_menu_items.asm','asm/battle/determine_targetting.asm')
PINNED=('ccscript/main.ccs','ccscript/redux/six_letters.ccs','ccscript/redux/naming_screen_table.ccs','ccscript/essential/stdext.ccs','ccscript/data/data_48.ccs','ccscript/data/data_49.ccs','ccscript/bugfixes/text_highlights_fix.ccs')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def h(b):return hashlib.sha256(b).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def main():
 ap=argparse.ArgumentParser(description=__doc__)
 for n in ('baseline-source','candidate-source','baseline-runtime','candidate-runtime','project','original-rom','redux-rom','original-assets','redux-assets','bridge','patch','source-review','manifest'):ap.add_argument('--'+n,type=Path,required=True)
 a=ap.parse_args()
 for n,v in vars(a).items():setattr(a,n,v.resolve())
 for p in (a.patch,a.source_review,a.manifest):
  if p.exists():raise ValueError('Fresh output required: '+str(p))
 baseline={str(p.relative_to(a.baseline_source)).replace('\\','/'):sha(p)for p in a.baseline_source.rglob('*')if p.is_file()}
 candidate={str(p.relative_to(a.candidate_source)).replace('\\','/'):sha(p)for p in a.candidate_source.rglob('*')if p.is_file()}
 changed=sorted(k for k in baseline.keys()|candidate.keys()if baseline.get(k)!=candidate.get(k))
 if changed!=sorted(FILES):raise ValueError('Private source lease was exceeded: '+str(changed))
 patch=''.join(''.join(difflib.unified_diff((a.baseline_source/p).read_text(encoding='utf-8').splitlines(True),(a.candidate_source/p).read_text(encoding='utf-8').splitlines(True),fromfile='a/'+p,tofile='b/'+p))for p in FILES)
 a.patch.write_text(patch,encoding='utf-8',newline='')
 reports={p:load(ROOT/p)for p in REPORTS}
 for p in REPORTS[:4]:
  if not reports[p]['nativeControlsPassed']:raise ValueError('Parent semantics failed: '+p)
 for p in (REPORTS[1],REPORTS[3],REPORTS[5]):
  r=reports[p];valid=r.get('sourceExpectedPassed',r.get('allPassed'))
  if not valid:raise ValueError('Private green is not green: '+p)
 red,green=reports[REPORTS[4]],reports[REPORTS[5]];exclusions=[]
 for b,c in zip(red['results'],green['results']):
  if (b['build'],b['profile'],b['names'])!=(c['build'],c['profile'],c['names']):raise ValueError('Control pairing differs')
  generic=all(x==y for x,y in zip(b['observations'],c['observations'])if x['test'].startswith('generic'))
  original_ascii=(b['profile']=='original'or b['names']=='ascii')
  rows_unchanged=not original_ascii or b['observations']==c['observations']
  title=b['titleControl']==c['titleControl'];hppp=b['hpppControl']==c['hpppControl'];structures=b['structures']==c['structures']
  if not all((generic,rows_unchanged,title,hppp,structures)):raise ValueError('Existing control changed')
  exclusions.append(dict(build=b['build'],profile=b['profile'],names=b['names'],genericAsciiRendererUnchanged=generic,originalAndAsciiNameRowsUnchanged=rows_unchanged,tinyTitleBytesAndActualVramUnchanged=title,hpppNameGlyphPlanesUnchanged=hppp,serializedStructSizesUnchanged=structures))
 bridge=load(a.bridge);rom=a.redux_rom.read_bytes();original=a.original_rom.read_bytes()
 if bridge['source']['revision']!=PIN or bridge['roms']['compiled']['sha256'].lower()!=h(rom):raise ValueError('Pinned bridge/ROM identity mismatch')
 labels={(r['module'],r['name']):r['snesAddress']for r in bridge['labels']};matrices=naming_matrices(rom,labels);legal={g for k in ('main_capital','main_small')for row in matrices[k]for g in row if g!=255}
 fonts=[]
 for profile,r,pak in [('original',original,a.original_assets),('redux',rom,a.redux_assets)]:
  _,_,assets=read_pack(pak,a.baseline_source/'src/data/runtime_generated/asset_ids.h');wp,gp,stride,height=struct.unpack_from('<IIHH',r,0x3f054);widths=assets['US/fonts/main.bin'];graphics=assets['US/fonts/main.gfx']
  equal=widths==r[wp-0xc00000:wp-0xc00000+len(widths)] and graphics==r[gp-0xc00000:gp-0xc00000+len(graphics)]
  if not equal:raise ValueError('Independent packed source font comparison differs')
  fonts.append(dict(profile=profile,packSha256=sha(pak),romSha256=h(r),widthPointer=wp,glyphPointer=gp,stride=stride,height=height,convertedGlyphCount=len(widths),widthsSha256=h(widths),graphicsSha256=h(graphics),exactSourceFontBytesMatch=True))
 fixtures=[row for p in (REPORTS[1],REPORTS[3])for row in reports[p]['results']if row['profile']=='redux'];fixture_glyphs={g for row in fixtures for name in row['preparedNames']for g in name}
 if not fixture_glyphs<=legal:raise ValueError('Prepared Redux names include a nonselectable glyph')
 if not all(row['sourceLegalNames']for row in fixtures):raise ValueError('Source legal name bounds differ')
 stops=[]
 for address in (0xc124d7,0xc12898):
  at=address-0xc00000; expected_old=bytes.fromhex('9ca49c');expected_new=bytes.fromhex('9ca59c')
  if original[at:at+3]!=expected_old or rom[at:at+3]!=expected_new:raise ValueError('Source raw-glyph terminator hook differs')
  stops.append(dict(address=address,originalInstruction='STZ temporary_text_buffer+5',reduxInstruction='STZ temporary_text_buffer+6',originalInstructionSha256=h(expected_old),reduxInstructionSha256=h(expected_new),actualMachineBytesChecked=True))
 source=dict(schemaVersion=1,proof='dev19-raw-party-name-menu-source-contract',upstreamRevision=PIN,bridgeSha256=sha(a.bridge),roms=dict(original=h(original),redux=h(rom)),exactMachineHookChecks=stops,packedFontChecks=fonts,sourceSelectableGlyphCount=len(legal),fixtureDistinctGlyphCount=len(fixture_glyphs),fixtureExtendedKeyboardGlyphs=sorted(g for g in fixture_glyphs if g>=0xb0 or g in (0xac,0xae,0xaf)),allPreparedReduxNameGlyphsSelectable=True,sourceNameCapacity=6,sourceMaximumNamePixels=40,activeRawNameMenuProducers=[dict(file='src/game/battle.c',symbol='char_select_overworld_prepare',source='CHAR_SELECT_PROMPT → raw GET_PARTY_CHARACTER_NAME → six-byte copy/terminator → ADD_MENU_ITEM → PRINT_MENU_ITEMS',consumers=['battle_targeting.c TGT_ENTER/ACTION_TARGET_ONE ally: ordinary Goods Use and PSI Lifeup/Healing','game_main.c debug Goods developer-only'],actualParents=['Goods refreshing herb','PSI Lifeup alpha','PSI Healing alpha','PSI Healing beta cancel']),dict(file='src/game/display_text.c',symbol='party_selector_overworld_prepare',source='PARTY_CHARACTER_SELECTOR mode1 → raw GET_PARTY_CHARACTER_NAME → six-byte copy/terminator → ADD_MENU_ITEM → PRINT_MENU_ITEMS',consumers=['CC1A00/01 mode1 through cc_1a_dispatch','source doctor C90000→C9105F','source nurse C9008D→C9128D','source healer C916A3→C91905','release-disabled/developer debug status/level callers'],actualParents=['complete Onett doctor illness5 PC2 wrapper','complete Onett nurse revive PC1 wrapper','complete Onett healer treatment0 PC1 wrapper'])],sourceReferences=[dict(path=p,sha256=sha(a.baseline_source/p))for p in ASMS],pinnedReferences=[dict(path=p,sha256=sha(a.project/p))for p in PINNED],focusedProducerSearch='All C EB-to-ASCII conversions of maternalbound_character_name/name_of or pet_name feeding add_menu_item were reviewed; two producer blocks above. Ending/raw battle text and already-reviewed title/file-slot paths remain separate. This is not a whole-program reachability proof.',implementation=dict(files=list(FILES),representation='Existing bounded single-byte label: reversible ASCII plus preserved high EB glyphs, using unchanged eb_to_title_buf.',consumer='Only normal party-name windows51 and41..43 with PC1..4/King7 userdata join the existing file-slot glyph decoder; both actual printing and width-aware highlight use it.',schema='MenuItem, WindowInfo and stateformat16 unchanged; no new fields, packs, assets, dialogue or Give/HPPP opcode changes.'),limits=['Machine-byte checks bind the actual pinned name-terminator hooks; full original CPU UI rasterization/parent execution is not claimed. Actual pixels use source-exact packed-font bytes and an independent compositor.', 'Complete selected native parents prepare legal party/status/inventory prerequisites before entry; natural map acquisition, all doctor towns, all PSI/item branches and physical controls remain unproved.', 'The direct King/pet branch and counts1..4 exercise source helper contracts, not a claim that King belongs to the ordinary player-controlled party.', 'Save16 cold captures restore actual rendered-menu state in fresh processes; previously captured pre-fix labels already containing question marks require the parent menu to be rebuilt to recover source glyphs.'],rootOrOwnerInputsModified=False)
 a.source_review.write_text(json.dumps(source,indent=2)+'\n',encoding='utf-8')
 summaries=[]
 for p in REPORTS[:4]:
  r=reports[p];summaries.append(dict(path=p,cases=len(r['results']),coldCases=sum(x['cold']for x in r['results']),nativeParentControlsPassed=r['nativeControlsPassed'],sourceFailures=sum(not x['sourceExpectedPassed']for x in r['results']),sourceExpectedPassed=r['sourceExpectedPassed']))
 payloads=[*REPORTS,*TOOLS,str(a.patch.relative_to(ROOT)).replace('\\','/'),str(a.source_review.relative_to(ROOT)).replace('\\','/')]
 items=[dict(path=p,sha256=sha(ROOT/p),bytes=(ROOT/p).stat().st_size)for p in payloads]
 # Bind the exact private candidate binaries and immutable shipping baseline.
 runtimes={label:{n:sha(folder/n)for n in ('player.exe','observer.exe','SDL2.dll')}for label,folder in [('baselineDev18V2',a.baseline_runtime),('privateDev19',a.candidate_runtime)]}
 checks=dict(parentSummaries=summaries,allGreenParentSequences=128,greenColdContinuations=64,boundedNativeRenderObservations=sum(len(x['observations'])for x in green['results']),boundedGreenSets=len(green['results']),allBoundedControlsPassed=green['allPassed'],existingBehaviorComparisons=exclusions)
 manifest=dict(schemaVersion=1,proof='private-dev19-party-name-glyph-proposal-final',privateOnly=True,baseCheckpoint='dev18-v2',upstreamRevision=PIN,changedFiles=[dict(path=p,baselineSha256=baseline[p],candidateSha256=candidate[p])for p in FILES],onlyThreeAuthorizedSourceFilesChanged=True,baselineSourceFiles=len(baseline),runtimes=runtimes,assets={label:sha(p)for label,p in [('original',a.original_assets),('redux',a.redux_assets)]},checks=checks,files=items,oldDev18EvidencePreserved=True,rootOrOwnerInputsModified=False,fullConversionVerified=False,fullPlaythroughVerified=False,limits=source['limits'])
 a.manifest.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(patch=str(a.patch),patchSha256=sha(a.patch),sourceReview=str(a.source_review),manifest=str(a.manifest),manifestSha256=sha(a.manifest),checks=checks,changedFiles=manifest['changedFiles'])),flush=True)
if __name__=='__main__':main()
