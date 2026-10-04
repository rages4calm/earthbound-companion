"""Trace reachable Redux movement bytecode against the native interpreter.

This is a structural audit, not proof that every story event was played.
Never interpret animation records or 65816 routine bodies as movement code.
Unknown calls stop that path so their operands cannot create false results.
"""
import argparse
from collections import Counter, defaultdict, deque
import hashlib
import json
from pathlib import Path
import re
import struct


def audit(assets, native_source):
    source=(native_source/"src/entity/opcodes.c").read_text(encoding="utf-8")
    table=source.split("opcode_arg_sizes[0x45] = {",1)[1].split("};",1)[0]
    sizes={int(op,16):int(size,0) for op,size in re.findall(r"/\* 0x([0-9A-Fa-f]+).*?\*/\s*(0xFF|\d+),",table)}
    if len(sizes)!=69: raise RuntimeError("Unexpected native opcode table")
    # Redux replaces the old background-scroll opcodes with task operations.
    sizes.update({0x32:0,0x33:0})
    header=(native_source/"src/data/event_script_data.h").read_text(encoding="utf-8")
    definitions={name:int(value,16) for name,value in re.findall(r"#define (ROM_ADDR_\w+)\s+(0x[0-9A-Fa-f]+)",header)}
    extras={int(value,16):int(count) for value,count in re.findall(r"#define ROM_ADDR_\w+\s+(0x[0-9A-Fa-f]+)\s*/\*\s*(\d+) extra byte",header)}
    extras.update({definitions["ROM_ADDR_SPAWN_ENTITY"]:2,
                   definitions["ROM_ADDR_SET_ENTITY_DIRECTION_AND_FRAME"]:2,
                   definitions["ROM_ADDR_MOVEMENT_CMD_LOOP"]:3})
    dispatcher=(native_source/"src/entity/callroutine.c").read_text(encoding="utf-8")
    cases=re.findall(r"case (ROM_ADDR_\w+|0x[0-9A-Fa-f]+):",dispatcher.split("int16_t callroutine_dispatch",1)[1])
    supported={definitions[c] if c in definitions else int(c,16) for c in cases}
    known=dispatcher.split("known_callroutine_addrs[]",1)[1].split("};",1)[0]
    recovered={}
    for name in re.findall(r"ROM_ADDR_\w+",known): recovered.setdefault(definitions[name]&0xFFFF,definitions[name])
    raw=assets["US/events/bank_c3_scripts_combined.bin"]
    magic,count=struct.unpack_from("<8sI",raw)
    if magic!=b"MRMVBN01": raise RuntimeError("Not a Redux movement container")
    cursor=12;regions=[]
    for _ in range(count):
        bank,reserved,base,length=struct.unpack_from("<BBHI",raw,cursor);cursor+=8
        if reserved or length>0x10000-base or cursor+length>len(raw): raise RuntimeError("Malformed movement region")
        regions.append(((bank<<16)+base,raw[cursor:cursor+length]));cursor+=length
    if cursor!=len(raw): raise RuntimeError("Trailing movement container data")
    def read(address,length):
        for base,data in regions:
            if base<=address and address+length<=base+len(data): return data[address-base:address-base+length]
        raise ValueError(f"Unavailable bytes at {address:06X} ({length})")
    pointers=assets["US/events/event_script_pointers.bin"]
    roots=[int.from_bytes(pointers[i:i+3],"little") for i in range(3,len(pointers),3)]
    pending=deque((address,f"script {i+1}") for i,address in enumerate(roots))
    visited=set();errors={};calls=defaultdict(set);opcodes={};edges=0
    flow={};returns={}
    def queue(address,origin):
        nonlocal edges
        edges+=1;pending.append((address,origin));flow[current].append(address)
    while pending:
        address,origin=pending.popleft()
        if address in visited: continue
        visited.add(address)
        current=address;flow[address]=[];returns[address]=("normal",[])
        try:
            opcode=read(address,1)[0]
            if opcode>=0x70: opcode=0x3B+((opcode&0x70)>>4)
            if opcode not in sizes:
                raise ValueError(f"Unknown opcode {opcode:02X} at {address:06X}")
            size=sizes[opcode];opcodes[address]=opcode
            if size==255: size=1+read(address+1,1)[0]*2
            data=read(address+1,size);end=address+1+size
            returns[address]=("normal",[end])
            def short(offset=0): return (address&0xFF0000)|int.from_bytes(data[offset:offset+2],"little")
            if opcode in (0x00,0x05,0x09,0x0C,0x1B):
                returns[address]=("return" if opcode in (0x05,0x1B) else "stop",[])
                continue
            if opcode in (0x03,0x04,0x31):
                queue(int.from_bytes(data,"little"),f"{address:06X} far branch")
                if opcode==0x03:
                    returns[address]=("normal",[int.from_bytes(data,"little")]);continue
                if opcode==0x04: returns[address]=("call",[int.from_bytes(data,"little"),end])
            elif opcode in (0x07,0x0A,0x0B,0x16,0x17,0x19,0x1A):
                queue(short(),f"{address:06X} short branch")
                if opcode==0x19:
                    returns[address]=("normal",[short()]);continue
                if opcode==0x1A: returns[address]=("call",[short(),end])
                elif opcode!=0x07: returns[address][1].append(short())
            elif opcode in (0x10,0x11):
                for i in range(data[0]): queue(short(1+i*2),f"{address:06X} switch")
                if opcode==0x10: returns[address][1].extend(short(1+i*2) for i in range(data[0]))
            elif opcode==0x42:
                routine=int.from_bytes(data,"little")
                if routine>>16==0: routine=recovered.get(routine,routine)
                calls[routine].add(address)
                if routine not in supported: raise ValueError(f"Unsupported routine {routine:06X} at {address:06X}")
                extra=extras.get(routine,0)
                if routine==definitions["ROM_ADDR_CHOOSE_RANDOM"]: extra=1+read(end,1)[0]*2
                operands=read(end,extra);end+=extra
                returns[address]=("normal",[end])
                if routine==definitions["ROM_ADDR_MOVEMENT_CMD_LOOP"]:
                    queue((address&0xFF0000)|int.from_bytes(operands[1:3],"little"),f"{address:06X} routine loop")
                    returns[address][1].append((address&0xFF0000)|int.from_bytes(operands[1:3],"little"))
            queue(end,f"{address:06X} fallthrough")
        except ValueError as error:
            errors[address]=f"{error}; reached from {origin}"
            returns[address]=("stop",[])
    # Least fixed point of possible return paths. A far/short call can reach
    # its continuation only if the callee can return. Some title helpers
    # intentionally halt forever, with no bytecode after their caller.
    can_return={addr for addr,(kind,_) in returns.items() if kind=="return"}
    while True:
        added={addr for addr,(kind,targets) in returns.items() if addr not in can_return and
               ((kind=="normal" and any(t in can_return for t in targets)) or
                (kind=="call" and all(t in can_return for t in targets)))}
        if not added: break
        can_return.update(added)
    reachable=set();pending=deque(roots)
    while pending:
        address=pending.popleft()
        if address in reachable: continue
        reachable.add(address)
        targets=flow.get(address,[])
        kind,dependencies=returns.get(address,("stop",[]))
        if kind=="call" and dependencies[0] not in can_return:
            targets=[t for t in targets if t!=dependencies[1]]
        pending.extend(targets)
    references=defaultdict(lambda:defaultdict(list))
    for address,opcode in opcodes.items():
        if address not in reachable: continue
        if opcode in (0x08,0x22,0x23,0x25):
            length=3 if opcode==0x08 else 2
            target=int.from_bytes(read(address+1,length),"little")
            references[f"callback-{opcode:02X}"][target].append(address)
        elif opcode in (0x0D,0x12,0x15,0x18,0x1E):
            target=int.from_bytes(read(address+1,2),"little")
            references[f"wram-{opcode:02X}"][target].append(address)
    references={kind:[{"Address":f"{target:06X}","Sites":[f"{site:06X}" for site in sites]}
                       for target,sites in sorted(targets.items())] for kind,targets in sorted(references.items())}
    errors=sorted(error for addr,error in errors.items() if addr in reachable)
    # Check targets, including the valid fallback callback addresses. A native
    # default branch is not evidence that an arbitrary pointer is supported.
    tick_source=(native_source/"src/entity/callroutine_screen.c").read_text(encoding="utf-8")
    tick_definitions={name:int(value,16) for name,value in re.findall(r"#define (TICK_ADDR_\w+)\s+(0x[0-9A-Fa-f]+)",tick_source)}
    tick_cases=re.findall(r"case (TICK_ADDR_\w+):",tick_source.split("void dispatch_tick_callback",1)[1])
    callback_targets={"callback-08":{tick_definitions[c] for c in tick_cases},
        "callback-22":{definitions["ROM_ADDR_DRAW_TITLE_LETTER"],definitions["ROM_ADDR_MOVE_NOP"]},
        "callback-23":{definitions[name] for name in ("ROM_ADDR_POS_COPY_ABS","ROM_ADDR_POS_NOP","ROM_ADDR_POS_SCREEN_BG3",
                           "ROM_ADDR_POS_BG1_WITH_Z","ROM_ADDR_POS_BG3_WITH_Z","ROM_ADDR_MOVE_FORCE_MOVE")}|{0xA023},
        "callback-25":{definitions[name] for name in ("ROM_ADDR_MOVE_FORCE_MOVE","ROM_ADDR_MOVE_PARTY_SPRITE",
                           "ROM_ADDR_MOVE_WITH_COLLISION","ROM_ADDR_MOVE_SIMPLE_COLLISION","ROM_ADDR_MOVE_DELTA_3D",
                           "ROM_ADDR_MOVE_Z_UPDATE","ROM_ADDR_MOVE_NOP","ROM_ADDR_MOVE_APPLY_DELTA")}}
    constants=(native_source/"src/include/constants.h").read_text(encoding="utf-8")
    counts={name:int(value) for name,value in re.findall(r"#define (MAX_ENTITIES|MAX_SCRIPTS)\s+(\d+)",constants)}
    counts["MAX_BG_LAYERS"]=4
    ranges=[]
    for kind,base in re.findall(r"WRAM_(ENT|SCR|BG|PATH)_TABLE\((0x[0-9A-Fa-f]+),",source):
        count=counts["MAX_SCRIPTS" if kind=="SCR" else "MAX_BG_LAYERS" if kind=="BG" else "MAX_ENTITIES"]
        ranges.append((int(base,16),int(base,16)+count*2))
    ranges.append((0x0E5E,0x0E5E+8*0x3C)) # entity variable tables' native loop
    scalars={int(value,16) for value in re.findall(r"WRAM_GLOBAL\((0x[0-9A-Fa-f]+),",source)}
    sentinel_definitions={name:int(value,16) for name,value in re.findall(r"#define (WRAM_\w+)\s+(0x[0-9A-Fa-f]+)",header)}
    wram_special={}
    for opcode,label,next_label in ((0x12,"case 0x12:","case OP_WRITE_WORD_WRAM:"),
                                    (0x15,"case OP_WRITE_WORD_WRAM:","case OP_SHORTJUMP:"),
                                    (0x1E,"case OP_WRITE_WRAM_TEMPVAR:","case 0x1F:")):
        body=source.split(label,1)[1].split(next_label,1)[0]
        tokens=re.findall(r"addr\s*==\s*(WRAM_\w+|0x[0-9A-Fa-f]+)",body)
        values={sentinel_definitions[t] if t in sentinel_definitions else int(t,16) for t in tokens}
        if opcode==0x12: values.update(int(value,16) for value in re.findall(r"case (0x[0-9A-Fa-f]+):",body))
        wram_special[f"wram-{opcode:02X}"]=values
    for kind,entries in references.items():
        for entry in entries:
            address=int(entry["Address"],16)
            if kind.startswith("callback"):
                supported=address in callback_targets[kind]
            else:
                supported=address in wram_special.get(kind,set()) or address in scalars or any(start<=address<end for start,end in ranges)
            entry["Resolved"]=supported
            if not supported: errors.append(f"Unhandled {kind} target {address:06X} at {entry['Sites'][0]}")
    opcodes=Counter(op for addr,op in opcodes.items() if addr in reachable)
    calls={addr:sites&reachable for addr,sites in calls.items() if sites&reachable}
    return {"Roots":len(roots),"Instructions":sum(opcodes.values()),"FlowEdges":sum(len(flow.get(a,[])) for a in reachable),
            "RoutineCalls":sum(len(sites) for sites in calls.values()),"DistinctRoutines":len(calls),
            "Opcodes":{f"{op:02X}":n for op,n in sorted(opcodes.items())},
            "Calls":[{"Address":f"{addr:06X}","Sites":[f"{s:06X}" for s in sorted(sites)]} for addr,sites in sorted(calls.items())],
            "References":references,
            "Errors":errors,"Passed":not errors,
            "Limits":["Static reachable bytecode and dispatch audit; no full story playthrough.",
                      "Routine and callback behavior, animation data and live story paths require separate validation."]}


def main():
    from build_maternalbound_pack import read_pack
    parser=argparse.ArgumentParser(description=__doc__)
    for option in ("assets","native-source","output"): parser.add_argument("--"+option,required=True,type=Path)
    args=parser.parse_args()
    _,_,assets=read_pack(args.assets,args.native_source/"src/data/runtime_generated/asset_ids.h")
    result=audit(assets,args.native_source)
    result["PackSha256"]=hashlib.sha256(args.assets.read_bytes()).hexdigest()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({key:result[key] for key in ("Roots","Instructions","RoutineCalls","DistinctRoutines","Passed")},indent=2))
    print("Errors:",len(result["Errors"]))
    raise SystemExit(0 if result["Passed"] else 1)


if __name__=="__main__": main()
