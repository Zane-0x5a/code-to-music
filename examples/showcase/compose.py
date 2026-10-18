"""Original, deterministic arrangements for the four public showcase scores.

Run with Python to regenerate the adjacent JSON scores. MIDI beat = quarter note.
The short examples one directory above remain unchanged as learning/test fixtures.
"""
from pathlib import Path
import json

HERE = Path(__file__).resolve().parent


def track(name, instrument, gain):
    return dict(id=name, instrument=instrument, gain_db=gain, events=[])


def note(t, beat, pitch, duration, velocity):
    t['events'].append(dict(type='note', beat=round(beat, 4), pitch=pitch,
                            duration=round(duration, 4), velocity=max(1, min(127, velocity))))


def chord(t, beat, pitches, duration, velocity, roll=0):
    for i, pitch in enumerate(pitches):
        note(t, beat+i*roll, pitch, duration-i*roll, velocity + (i % 3)-1)


def phrase(t, bar, notes, velocity=85, delay=0):
    for i, (offset, pitch, duration) in enumerate(notes):
        note(t, bar*4+offset+delay, pitch, duration, velocity+[0,-4,2,-2,1,-3][i%6])


def save(name, title, tempo, bars, tracks, tail=3, master=-3):
    # Avoid retrigger collisions within each voice without changing its attacks.
    for t in tracks:
        t['events'].sort(key=lambda e:(e['beat'],e.get('pitch',-1)))
        by_pitch={}
        for e in t['events']:
            if e['type']=='note': by_pitch.setdefault(e['pitch'],[]).append(e)
        for events in by_pitch.values():
            for previous,current in zip(events,events[1:]):
                assert current['beat']>previous['beat'], (name,t['id'],current)
                previous['duration']=round(min(previous['duration'],current['beat']-previous['beat']-.015),4)
        for e in t['events']:
            if e['type']=='note':
                e['duration']=round(min(e['duration'],bars*4-e['beat']),4)
                assert e['duration']>.001
    score=dict(version=1,title=title,tempo=tempo,time_signature=[4,4],length_beats=bars*4,
               output=dict(sample_rate=48000,tail_seconds=tail,master_gain_db=master,
                           stems=True,midi=True,intermediates=False),tracks=tracks)
    (HERE/f'{name}.json').write_text(json.dumps(score,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(name, f'{bars*4*60/tempo:.1f}s music', sum(len(t['events']) for t in tracks),'events')


def piano():
    # D major: a four-bar question, answer, rising bridge, then a settled cadence.
    melody=track('melody','salamander-piano',12)
    left=track('left_hand','salamander-piano',8)
    inner=track('inner_voice','salamander-piano',7)
    harmony=[
        (38,[50,57,61,66]), (35,[47,54,57,62]), (31,[43,50,57,59]), (33,[45,52,55,61]),
        (30,[42,49,57,61]), (35,[47,54,57,62]), (28,[40,47,55,59]), (33,[45,52,55,61]),
        (31,[43,50,55,59]), (30,[42,50,57,62]), (28,[40,47,55,59]), (33,[45,52,55,61]),
        (35,[47,54,57,62]), (31,[43,50,57,59]), (33,[45,52,55,61]), (38,[50,57,61,66]),
    ]
    lines=[
        [(0,69,.7),(.75,74,1.1),(2,78,.7),(2.75,76,.45),(3.25,74,.65)],
        [(0,73,.9),(1,74,.45),(1.5,78,.9),(2.5,76,.65),(3.25,73,.6)],
        [(0,71,1.35),(1.5,74,.4),(2,78,.8),(3,76,.8)],
        [(0,73,.9),(1,71,.7),(2,69,1.35),(3.5,73,.35)],
        [(0,69,.65),(.75,73,.65),(1.5,76,.9),(2.5,78,.65),(3.25,76,.6)],
        [(0,74,1.35),(1.5,73,.4),(2,71,.9),(3,69,.85)],
        [(0,67,.65),(.75,71,.65),(1.5,74,1.2),(3,73,.85)],
        [(0,71,.65),(.75,73,.65),(1.5,76,1.3),(3,73,.75)],
        [(0,74,.65),(.75,79,.65),(1.5,83,1.1),(2.75,81,.4),(3.25,79,.6)],
        [(0,78,1.35),(1.5,76,.4),(2,74,.7),(2.75,76,.45),(3.25,78,.6)],
        [(0,79,.65),(.75,78,.65),(1.5,76,.9),(2.5,74,.65),(3.25,71,.6)],
        [(0,73,.9),(1,76,.65),(1.75,81,1.05),(3,79,.75)],
        [(0,78,.7),(.75,76,.45),(1.25,74,1.1),(2.5,73,.65),(3.25,71,.6)],
        [(0,74,.9),(1,71,.65),(1.75,69,.65),(2.5,67,1.15)],
        [(0,69,.9),(1,73,.9),(2,76,.65),(2.75,73,.4),(3.25,69,.6)],
        [(0,74,3.65)],
    ]
    for bar,((root,voicing),line) in enumerate(zip(harmony,lines)):
        intensity=6 if 8<=bar<12 else (-5 if bar>=13 else 0)
        phrase(melody,bar,line,86+intensity,delay=.015 if bar!=15 else 0)
        note(left,bar*4,root,1.8,64+intensity)
        if bar==15:
            chord(left,bar*4+.04,voicing[:3],3.45,58,roll=.018)
            chord(inner,bar*4+.09,[66,69],3.3,54,roll=.025)
        else:
            order=[0,1,2,3,1,2,3] if bar%2==0 else [0,2,1,3,2,1,3]
            for i,index in enumerate(order):
                at=bar*4+.5+i*.5+([0,.015,-.008,.012][i%4])
                note(left,at,voicing[index],.62,53+intensity+[1,5,-3,2,0,-2,3][i])
            if bar>=4:
                note(inner,bar*4+2.05,voicing[-1]+12,.8,52+intensity)
        for t in [melody,left,inner]:
            t['events'].append(dict(type='cc',beat=bar*4+.025,controller=64,value=100))
            t['events'].append(dict(type='cc',beat=bar*4+3.88,controller=64,value=0))
    save('window-light','Window Light / 窗边微光',92,16,[melody,left,inner],tail=2.5,master=0)


def drums():
    # A drummer's 16-bar performance: restrained pocket, fuller groove, break, return.
    kit=track('kit','avl-red-zeppelin',7)
    kicks=[[0,1.75,2.5],[0,.75,2,2.75],[0,1.5,2.5,3.75],[0,2,2.75]]
    for bar in range(16):
        b=bar*4
        if bar==15:
            for off,p,v in [(0,36,112),(0,49,100),(.75,38,68),(1,48,88),(1.5,45,94),
                             (2,43,102),(2.5,38,116),(3,36,112),(3,49,99)]:
                note(kit,b+off,p,.22,v)
            continue
        if bar in [8,9]:
            # Two-bar break: space, cross-stick and a reply from the toms.
            for off,p,v in [(0,36,101),(1.025,37,82),(2.5,36,91),(3.025,37,88)]:
                note(kit,b+off,p,.15,v)
            for i in range(4): note(kit,b+i,42,.1,54+5*(i%2))
            if bar==9:
                for off,p,v in [(3.5,48,72),(3.75,45,82)]: note(kit,b+off,p,.18,v)
            continue
        for i,off in enumerate(kicks[bar%4]): note(kit,b+off,36,.18,106-[0,12,5,16][i%4])
        for off in [1.022,3.026]: note(kit,b+off,38,.18,104+(bar%3)*3)
        if bar>=2:
            for off,v in [(1.72,39),(2.82,46)]: note(kit,b+off,38,.08,v+(bar%2)*4)
        # Tiny sixteenth swing and alternating accents, not random quantization.
        dense=bar in [5,6,12,13]
        for i in range(16 if dense else 8):
            off=i*(.25 if dense else .5)
            if dense and i%2: off+=.035
            off+=.008 if i%2 else 0
            pitch=46 if i==(15 if dense else 7) and bar in [2,6,10,13] else (51 if 10<=bar<=11 else 42)
            velocity=([74,38,56,42] if dense else [75,51,66,48])[i%4]+bar%3
            if bar in [3,7,11,14] and off>=3: continue
            note(kit,b+off,pitch,.12 if pitch!=46 else .28,velocity)
        if bar in [0,4,10,12]: note(kit,b,49,.3,88 if bar==0 else 99)
        if bar in [3,7,11,14]:
            fill=[(3,38,88),(3.25,38,60),(3.5,48,91),(3.75,45,100)]
            if bar==7: fill=[(3,38,95),(3.25,48,93),(3.5,45,101),(3.75,43,110)]
            # Replace backbeat at beat 3 with the first fill hit.
            kit['events']=[e for e in kit['events'] if not (e['pitch']==38 and b+3<=e['beat']<b+3.1)]
            for off,p,v in fill: note(kit,b+off,p,.15,v)
    save('pocket-workshop','Pocket Workshop / 律动工坊',108,16,[kit],tail=6,master=0)


def orchestra():
    # G-major chamber miniature; no fake brass staccato or unsupported expression CC.
    flute=track('flute','vsco-flute-sustain',7)
    trumpet=track('trumpet','vsco-trumpet-sustain',1)
    strings=track('strings','vsco-violin-ensemble',4)
    harmony=[[55,62,67],[59,62,67],[60,64,67],[57,62,66],
             [59,64,67],[60,64,69],[57,62,66],[55,62,67],
             [60,64,67],[59,62,67],[57,60,66],[55,62,67]]
    flute_lines={
      0:[(0,74,.85),(1,79,1.35),(2.5,78,.4),(3,76,.8)],
      1:[(0,74,1.4),(1.5,71,.4),(2,74,1.65)],
      2:[(0,76,.85),(1,79,.85),(2,81,.65),(2.75,79,.4),(3.25,76,.5)],
      3:[(0,78,1.4),(1.5,76,.4),(2,74,1.65)],
      6:[(0,81,.8),(1,78,.8),(2,76,.8),(3,74,.75)],
      7:[(0,79,2.4),(2.75,81,.35),(3.25,83,.45)],
      8:[(0,84,1.35),(1.5,83,.4),(2,81,.85),(3,79,.75)],
      9:[(0,83,.85),(1,81,.85),(2,79,1.65)],
      10:[(0,78,.85),(1,76,.85),(2,74,1.65)],
      11:[(0,79,3.65)],
    }
    trumpet_lines={
      2:[(0,60,1.75),(2,64,1.65)], 3:[(0,62,2.8)],
      4:[(0,67,.9),(1,71,1.3),(2.5,69,.4),(3,67,.75)],
      5:[(0,69,1.3),(1.5,67,.4),(2,64,1.65)],
      6:[(.5,66,1.25),(2.5,69,1.15)], 7:[(0,67,3.3)],
      8:[(0,67,1.7),(2,72,1.7)], 9:[(0,71,1.7),(2,67,1.7)],
      10:[(0,66,1.7),(2,62,1.7)], 11:[(0,67,3.5)],
    }
    for bar,voicing in enumerate(harmony):
        dynamics=[60,62,66,63,65,68,73,76,85,81,74,64][bar]
        if bar in [6,7,8,9]:
            for j in range(4): chord(strings,bar*4+j,voicing,.88,dynamics+[0,-5,3,-4][j],roll=.008)
        else:
            chord(strings,bar*4,voicing,3.78,dynamics,roll=.014)
        if bar in flute_lines: phrase(flute,bar,flute_lines[bar],79+(7 if bar>=8 and bar<10 else 0))
        if bar in trumpet_lines: phrase(trumpet,bar,trumpet_lines[bar],77 if 4<=bar<=5 else 65+(10 if bar==8 else 0),.018)
    save('morning-path','Morning Path / 林间晨行',88,12,[flute,trumpet,strings],tail=2.2,master=-2)


def electronic():
    # D minor, 16 bars: intro 2 / A 4 / variation 2 / breakdown 2 / B 4 / cadence 2.
    ep=track('electric_piano','surge-dx-ep',0)
    bass=track('bass','surge-e-bass',-2)
    pluck=track('pluck','surge-nice-pluck',-6)
    lead=track('lead','surge-classic-lead',-10)
    pad=track('pad','surge-fm-pad',-12)
    kit=track('drums','avl-black-pearl',3)
    roots=[38,34,38,34,41,36,31,33,34,36,38,34,41,36,33,38]
    voicings=[[57,60,64,65],[57,60,62,65],[57,60,64,65],[57,60,62,65],
              [57,60,64,67],[55,60,64,67],[55,58,62,65],[55,61,64,69],
              [57,60,62,65],[55,60,64,67],[57,60,64,65],[57,60,62,65],
              [57,60,64,67],[55,60,64,67],[55,61,64,69],[57,60,64,65]]
    lead_lines={
      2:[(.5,74,.65),(1.5,77,.4),(2.25,76,.45),(3,74,.65)],
      3:[(0,72,.85),(1.5,74,.4),(2.5,69,1.1)],
      4:[(.5,72,.65),(1.5,77,.4),(2.25,79,.45),(3,81,.65)],
      5:[(0,79,.85),(1.5,76,.4),(2.25,74,.45),(3,72,.65)],
      6:[(.5,74,.4),(1.25,77,.45),(2,79,.85),(3.25,77,.45)],
      7:[(0,76,.65),(1,73,.65),(2,69,1.4)],
      10:[(0,81,.65),(.75,77,.45),(1.5,74,.45),(2.25,76,.45),(3,77,.65)],
      11:[(0,79,.65),(.75,77,.45),(1.5,74,.85),(2.75,72,.4),(3.25,74,.45)],
      12:[(.5,77,.65),(1.5,81,.4),(2.25,84,.45),(3,81,.65)],
      13:[(0,79,.85),(1,76,.4),(1.75,74,.45),(2.5,72,1.1)],
      14:[(0,73,.65),(.75,76,.45),(1.5,79,.65),(2.5,76,.4),(3.25,73,.45)],
      15:[(0,74,3.2)],
    }
    for bar,(root,voice) in enumerate(zip(roots,voicings)):
        b=bar*4
        breakdown=bar in [8,9]
        # Syncopated chord stabs leave room around the melodic attacks.
        stabs=[(0,2.5,66)] if bar==0 else ([(0,3.4,64)] if breakdown or bar==15 else [(0,.7,77),(1.75,.48,69),(2.75,.7,74)])
        for off,dur,vel in stabs: chord(ep,b+off,voice,dur,vel,roll=.008)
        if bar in [0,2,4,6,8,10,12,14,15]:
            chord(pad,b,[p+12 for p in voice[:3]],3.1 if bar>=14 else 7.1,55 if bar<10 else 63,roll=.01)
        if bar!=0:
            if breakdown: note(bass,b,root,2.7,79)
            elif bar==15: note(bass,b,root,3.25,101)
            else:
                next_root=roots[bar+1]
                approach=next_root-1 if next_root>root else next_root+1
                for off,p,dur,vel in [(0,root,.65,104),(.75,root,.35,83),(1.5,root+12,.35,91),
                                       (2.25,root,.6,99),(3.25,root+7,.3,85),(3.75,approach,.18,75)]:
                    note(bass,b+off,p,dur,vel)
        if bar in [0,1,6,7,8,9,10,11,12,13,14]:
            pattern=[0,2,1,3,2,1,3,2]
            for i,index in enumerate(pattern):
                if breakdown and i%2: continue
                note(pluck,b+i*.5+.03,voice[index]+12,.22,66+[7,-8,1,-5][i%4]-(7 if breakdown else 0))
        if bar in lead_lines: phrase(lead,bar,lead_lines[bar],85 if bar<10 else 93,.01)
        if bar==15:
            note(kit,b,36,.2,110); note(kit,b,49,.4,92)
            continue
        if bar==8: continue
        if bar==9:
            for i in range(8): note(kit,b+2+i*.25,38,.1,42+i*7)
            continue
        if bar==0:
            for i in range(8): note(kit,b+i*.5,42,.1,55+[4,-7][i%2])
            continue
        for off,v in [(0,110),(1.5,88),(2,103),(3.5,88)]: note(kit,b+off,36,.16,v)
        for off in [1.012,3.012]: note(kit,b+off,38,.16,99+(bar%2)*5)
        for i in range(8):
            pitch=46 if i==7 and bar%2 else 42
            note(kit,b+i*.5+.008*(i%2),pitch,.12 if pitch==42 else .24,[70,46,58,49][i%4])
        if bar in [2,10]: note(kit,b,49,.3,85)
        if bar in [5,7,13,14]:
            note(kit,b+2.75,38,.08,43)
            for off,p,v in [(3.5,48,76),(3.75,45,87)]: note(kit,b+off,p,.12,v)
    save('after-hours','After Hours / 夜航',112,16,[ep,bass,pluck,lead,pad,kit],tail=3,master=0)


if __name__=='__main__':
    piano()
    drums()
    orchestra()
    electronic()
