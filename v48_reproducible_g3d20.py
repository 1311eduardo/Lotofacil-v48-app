#!/usr/bin/env python3
"""V4.8-Reproducible / G3-D20
Engineering reconstruction of V4.7 mathematical architecture.
No claim of reproducing the lost V4.7 RNG stream.
"""
from __future__ import annotations
import hashlib, itertools, json, random
from collections import Counter
from typing import Iterable

ENGINE = "V4.8-Reproducible / G3-D20"
PARENT = "V4.7-Official / G3-D20"
N_NUMBERS, GAME_SIZE = 25, 15
CANDIDATES, TOP_K, PORTFOLIO_SIZE, OVERLAP_MAX = 5000, 800, 20, 13

CONFIG = {
    "engine": ENGINE, "parent_architecture": PARENT,
    "math_change_from_v47": False,
    "candidate_generation": {"count":5000, "keep_structural_top":800,
        "rng":"Python random.Random(MT19937)",
        "seed_rule":"first 64 bits of SHA256(canonical seed material), big-endian",
        "unique_candidates":True},
    "structural": {"sum_center":195,"sum_scale":30,"odd_center":7.5,"odd_scale":2.5,
        "group_target":3,"group_scale":10,"repeat_center":9,"repeat_scale":3},
    "core_weights":{"struct":.50,"newcov":.20,"balance":.15,"diversity":.15},
    "expansion_weights":{"struct":.70,"overlap_geometry":.10,"balance":.08,
                         "pair_novelty":.07,"triple_novelty":.05},
    "overlap_max":13,"portfolio_size":20,
    "tie_break":"highest score, then lexicographically smallest candidate",
    "serialization":"canonical JSON UTF-8 sort_keys=True separators=(',',':')"
}
def canonical(obj): return json.dumps(obj, sort_keys=True, separators=(",",":"), ensure_ascii=False)
CONFIG_SHA256 = hashlib.sha256(canonical(CONFIG).encode()).hexdigest()

def seed_for(target_contest:int, previous_draw:Iterable[int]) -> int:
    material={"engine":ENGINE,"target_contest":int(target_contest),
              "previous_draw":sorted(map(int,previous_draw)),"config_sha256":CONFIG_SHA256}
    return int.from_bytes(hashlib.sha256(canonical(material).encode()).digest()[:8],"big")

def structural(g, prev):
    g=set(g); prev=set(prev)
    sm=sum(g); odd=sum(n%2 for n in g)
    groups=[sum(lo<=n<=lo+4 for n in g) for lo in (1,6,11,16,21)]
    rep=len(g&prev)
    zsum=abs(sm-195)/30
    zodd=abs(odd-7.5)/2.5
    zgrp=sum(abs(x-3) for x in groups)/10
    zrep=abs(rep-9)/3
    return 1-(zsum+zodd+zgrp+zrep)/4

def generate_candidates(target, prev):
    rng=random.Random(seed_for(target,prev)); seen=set(); out=[]
    universe=list(range(1,26))
    while len(out)<CANDIDATES:
        g=tuple(sorted(rng.sample(universe,GAME_SIZE)))
        if g not in seen: seen.add(g); out.append(g)
    out.sort(key=lambda g:(-structural(g,prev),g))
    return out[:TOP_K]

def overlap(a,b): return len(set(a)&set(b))
def usage_balance(selected, cand):
    c=Counter(n for g in selected for n in g); c.update(cand)
    vals=[c[n] for n in range(1,26)]
    return max(0.0,1-(max(vals)-min(vals))/10)

def diversity(selected,cand):
    if not selected: return 1.0
    return max(0.0,1-sum(overlap(cand,g) for g in selected)/(len(selected)*15))

def newcov(selected,cand):
    used={n for g in selected for n in g}
    return len(set(cand)-used)/15

def valid_overlap(selected,cand):
    return all(overlap(cand,g)<=OVERLAP_MAX for g in selected)

def select_core(cands,prev):
    sel=[]
    while len(sel)<5:
        pool=[g for g in cands if g not in sel and valid_overlap(sel,g)]
        def score(g):
            return .50*structural(g,prev)+.20*newcov(sel,g)+.15*usage_balance(sel,g)+.15*diversity(sel,g)
        sel.append(min(pool,key=lambda g:(-score(g),g)))
    return sel

def pairset(g): return set(itertools.combinations(g,2))
def tripleset(g): return set(itertools.combinations(g,3))

def select_expansion(cands,prev,sel):
    core=sel[:5]
    ovs=[overlap(a,b) for a,b in itertools.combinations(core,2)]
    target=sum(ovs)/len(ovs)
    seenp=set().union(*(pairset(g) for g in sel))
    seent=set().union(*(tripleset(g) for g in sel))
    while len(sel)<PORTFOLIO_SIZE:
        pool=[g for g in cands if g not in sel and valid_overlap(sel,g)]
        def score(g):
            meanov=sum(overlap(g,x) for x in core)/len(core)
            ovgeom=max(0.0,1-abs(meanov-target)/5)
            pn=len(pairset(g)-seenp)/105
            tn=len(tripleset(g)-seent)/455
            return .70*structural(g,prev)+.10*ovgeom+.08*usage_balance(sel,g)+.07*pn+.05*tn
        g=min(pool,key=lambda x:(-score(x),x))
        sel.append(g); seenp.update(pairset(g)); seent.update(tripleset(g))
    return sel

def generate(target_contest:int, previous_draw:Iterable[int]):
    prev=tuple(sorted(map(int,previous_draw)))
    c=generate_candidates(target_contest,prev)
    p=select_expansion(c,prev,select_core(c,prev))
    return [list(g) for g in p]

def snapshot(target_contest:int, previous_draw:Iterable[int], history_through:int):
    obj={"engine":ENGINE,"parent_architecture":PARENT,"target_contest":target_contest,
         "history_through":history_through,"previous_draw":sorted(map(int,previous_draw)),
         "config":CONFIG,"config_sha256":CONFIG_SHA256,
         "seed":seed_for(target_contest,previous_draw),
         "portfolio":generate(target_contest,previous_draw),
         "portfolio_size":20,"status":"FROZEN_BEFORE_RESULT_CHECK"}
    obj["snapshot_sha256"]=hashlib.sha256(canonical(obj).encode()).hexdigest()
    return obj

if __name__=="__main__":
    # Self-test: same inputs must be bit-identical.
    prev=[1,3,4,5,6,8,10,11,12,13,14,18,19,22,24]
    a=snapshot(3796,prev,3795); b=snapshot(3796,prev,3795)
    assert canonical(a)==canonical(b)
    print("SELF_TEST=PASS")
    print("CONFIG_SHA256="+CONFIG_SHA256)
    print("SEED_3796="+str(a["seed"]))
    print("SNAPSHOT_SHA256="+a["snapshot_sha256"])
