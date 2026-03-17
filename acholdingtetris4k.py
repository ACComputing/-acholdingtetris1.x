#!/usr/bin/env python3
"""
AC's Ultra!TETRIS — Game Boy Edition (60 FPS)

OST accuracy:
  - A-Type (Korobeiniki): 160 BPM exact.
    BT = 0.1875 s per eighth-note.
  - Lead  : 25% duty square wave  (GB CH1 register, most accurate to ROM)
  - Bass  : 50% duty square wave, one octave down, lower volume (GB CH2)
  - Gap   : 12% silence between notes — gives GB staccato articulation
  - Full A-A-B-A-C Korobeiniki loop exactly matching the original Game Boy ROM.
  - Full B-Type (Troika) and C-Type (French Suite) themes added!
"""

import math, pygame, sys, random, struct, array

SW, SH   = 600, 400
COLS, ROWS = 10, 20
BLK = 16;  FPS = 60
BRD_X = SW//2 - (COLS*BLK)//2
BRD_Y = SH//2 - (ROWS*BLK)//2 + 8

C0=(155,188,15); C1=(139,172,15); C2=(48,98,48); C3=(15,56,15)
PNAMES=['T','J','Z','O','S','L','I']

ROT = {
    'I':[[(0,1),(1,1),(2,1),(3,1)],[(2,0),(2,1),(2,2),(2,3)]],
    'O':[[(0,0),(1,0),(0,1),(1,1)]],
    'T':[[(0,0),(1,0),(2,0),(1,1)],[(1,0),(0,1),(1,1),(1,2)],
         [(1,0),(0,1),(1,1),(2,1)],[(1,0),(1,1),(2,1),(1,2)]],
    'J':[[(0,0),(1,0),(2,0),(2,1)],[(1,0),(1,1),(0,2),(1,2)],
         [(0,0),(0,1),(1,1),(2,1)],[(1,0),(2,0),(1,1),(1,2)]],
    'L':[[(0,0),(1,0),(2,0),(0,1)],[(0,0),(1,0),(1,1),(1,2)],
         [(2,0),(0,1),(1,1),(2,1)],[(1,0),(1,1),(1,2),(2,2)]],
    'S':[[(1,0),(2,0),(0,1),(1,1)],[(0,0),(0,1),(1,1),(1,2)]],
    'Z':[[(0,0),(1,0),(1,1),(2,1)],[(1,0),(0,1),(1,1),(0,2)]]
}
GRAV={0:53,1:49,2:45,3:41,4:37,5:33,6:28,7:22,8:17,9:11,
      10:10,11:9,12:8,13:7,14:6,15:6,16:5,17:5,18:4,19:4,20:3}
DAS_INIT=24; DAS_REP=9; ARE_FR=2
LSCORES={1:40,2:100,3:300,4:1200}

# ====================== AUDIO ======================
SR = 44100

def _pulse(freq, dur, duty=0.5, vol=0.3, decay=0.0):
    n = int(SR*dur)
    out = array.array('h')
    if n == 0: return out
    for i in range(n):
        if freq <= 0: out.append(0); continue
        t = i/SR
        w = 1.0 if (freq*t)%1.0 < duty else -1.0
        v = max(0.0, vol - decay*t)
        out.append(int(max(-32767, min(32767, w*v*32767))))
    return out

def _noise(dur, vol=0.15):
    n=int(SR*dur); out=array.array('h')
    for i in range(n):
        v=vol*max(0.0,1.0-(i/n))
        out.append(int(max(-32767,min(32767,random.choice([-1.0,1.0])*v*32767))))
    return out

def _snd(s): return pygame.mixer.Sound(buffer=struct.pack(f'<{len(s)}h',*s))

def _mix(*arrs):
    ml=max(len(a) for a in arrs); m=array.array('h',[0]*ml)
    for a in arrs:
        for i in range(len(a)): m[i]=int(max(-32767,min(32767,m[i]+a[i])))
    return m

# Full frequency table — octaves 2-5 + enharmonics
NF = {
    'C2':65.4,  'C#2':69.3, 'D2':73.4,  'D#2':77.8, 'E2':82.4,  'F2':87.3,  'F#2':92.5, 'G2':98.0,  'G#2':103.8,'A2':110.0, 'A#2':116.5,'B2':123.5,
    'C3':130.8, 'C#3':138.6,'D3':146.8, 'D#3':155.6,'E3':164.8, 'F3':174.6, 'F#3':185.0,'G3':196.0, 'G#3':207.7,'A3':220.0, 'A#3':233.1,'B3':246.9,
    'C4':261.6, 'C#4':277.2,'D4':293.7, 'D#4':311.1,'E4':329.6, 'F4':349.2, 'F#4':370.0,'G4':392.0, 'G#4':415.3,'A4':440.0, 'A#4':466.2,'B4':493.9,
    'C5':523.3, 'C#5':554.4,'D5':587.3, 'D#5':622.3,'E5':659.3, 'F5':698.5, 'F#5':740.0,'G5':784.0, 'G#5':830.6,'A5':880.0, 'A#5':932.3,'B5':987.8,
    'R':0,
}

# ---- tempo constants ----
BT    = 0.1875   # one eighth-note at 160 BPM  (60/(160*2) = 0.1875)
ARTIC = 0.88     # note-on ratio; 12% gap = GB staccato articulation

# ---- Korobeiniki (A-Type) ----
# Duration units: 1=eighth 2=quarter 3=dotted-quarter 4=half
_PA = [   # Part A — classic verse
    ('E5',2),('B4',1),('C5',1),('D5',2),('C5',1),('B4',1),
    ('A4',2),('A4',1),('C5',1),('E5',2),('D5',1),('C5',1),
    ('B4',3),('C5',1),('D5',2),('E5',2),
    ('C5',2),('A4',2),('A4',4),
]
_PB = [   # Part B — bridge (higher register)
    ('D5',2), ('F5',1), ('A5',1), ('G5',2), ('F5',2),
    ('E5',2), ('C5',1), ('E5',1), ('D5',2), ('C5',2),
    ('B4',2), ('B4',1), ('C5',1), ('D5',2), ('E5',2),
    ('C5',2), ('A4',2), ('A4',4),
]
_PC = [   # Part C — pedal section (Now added for the WHOLE song)
    ('E4',4),('C4',4),('D4',4),('B3',4),
    ('C4',4),('A3',4),('G#3',4),('B3',4),
    ('E4',4),('C4',4),('D4',4),('B3',4),
    ('C4',2),('E4',2),('A4',4),('G#4',4),('R',4)
]
MEL_A = _PA + _PA + _PB + _PA + _PC   # Full A-A-B-A-C before seamless loop

# ---- Troika (B-Type) ----
_MB1 = [
    ('E5',1),('E5',1),('E5',1),('B4',1), ('C5',1),('D5',1),('C5',1),('B4',1),
    ('A4',1),('A4',1),('G4',1),('F#4',1), ('E4',2),('R',2),
]
_MB2 = [
    ('G5',2),('F#5',1),('G5',1),('A5',2),('G5',2),
    ('F#5',2),('E5',1),('F#5',1),('G5',2),('F#5',2),
    ('E5',2),('D5',1),('E5',1),('F#5',2),('E5',2),
    ('D5',2),('C5',2),('B4',4)
]
MEL_B = _MB1 + _MB1 + _MB2 + _MB1

# ---- French Suite No. 3 Minuet (C-Type) ----
_MC = [
    ('F#4',2),('B4',1),('C#5',1),('D5',1),('E5',1),
    ('F#5',2),('B4',2),('B4',2),
    ('G5',2),('F#5',1),('E5',1),('D5',1),('C#5',1),
    ('D5',2),('C#5',2),('B4',2),
    ('E5',2),('D5',1),('C#5',1),('B4',1),('A#4',1),
    ('D5',2),('C#5',1),('B4',1),('A#4',1),('G#4',1),
    ('F#5',2),('E5',2),('D5',2),
    ('C#5',6)
]
MEL_C = _MC + _MC


def _build_ost(m_data):
    """
    Lead : 25% duty square (GB CH1) — the authentic nasal GB tone
    Bass : 50% duty square (GB CH2), octave down, lower vol
    Both : 12% articulation silence gap between every note
    """
    lead = array.array('h')
    bass = array.array('h')

    for note, d in m_data:
        full = d * BT
        on   = full * ARTIC
        off  = full * (1.0 - ARTIC)

        freq  = NF.get(note, 0)
        silence = _pulse(0, off, 0.25, 0, 0)

        # lead
        if freq > 0:
            lead.extend(_pulse(freq, on, duty=0.25, vol=0.34, decay=0.20))
        else:
            lead.extend(_pulse(0, on, 0.25, 0, 0))
        lead.extend(silence)

        # bass — one octave down
        bfreq = 0
        if note != 'R':
            bkey  = note[:-1] + str(int(note[-1]) - 1)
            bfreq = NF.get(bkey, 0)
        if bfreq > 0:
            bass.extend(_pulse(bfreq, on, duty=0.50, vol=0.17, decay=0.30))
        else:
            bass.extend(_pulse(0, on, 0.50, 0, 0))
        bass.extend(silence)

    return _snd(_mix(lead, bass))

def _build_sfx(name):
    if name=='move':     return _snd(_pulse(880,  .025,.5,.10,decay=2.0))
    if name=='rotate':   return _snd(_pulse(1200, .03, .5,.10,decay=3.0))
    if name=='land':     return _snd(_mix(_pulse(150,.05,.5,.1),_noise(.05,.1)))
    if name=='clear':    return _snd(_pulse(659,  .15, .5,.15,decay=1.5))
    if name=='tetris':
        s=array.array('h')
        for f in [523,659,784,1047]: s.extend(_pulse(f,.08,.5,.15))
        return _snd(s)
    if name=='gameover': return _snd(_pulse(200,.5,.5,.2,decay=1.0))
    if name=='menu':     return _snd(_pulse(740,.03,.5,.1))
    return None

# ====================== GRAPHICS ======================
def _font(sz): return pygame.font.SysFont('couriernew',sz,bold=True)

def dtc(srf,txt,f,c,y,cx=None):
    r=f.render(txt,True,c); srf.blit(r,((cx or SW//2)-r.get_width()//2,y))

def dblk(srf,x,y,name):
    P={'T':1,'J':0,'Z':2,'O':3,'S':2,'L':0,'I':1}; s=P.get(name,0)
    pygame.draw.rect(srf,C0,(x,y,BLK,BLK))
    if s==0:
        pygame.draw.rect(srf,C3,(x,y,BLK,BLK))
        pygame.draw.rect(srf,C1,(x+1,y+1,BLK-2,BLK-2))
        pygame.draw.rect(srf,C3,(x+3,y+3,BLK-6,BLK-6))
    elif s==1:
        pygame.draw.rect(srf,C3,(x,y,BLK,BLK),1)
        pygame.draw.rect(srf,C2,(x+1,y+1,BLK-2,BLK-2))
        for i in range(2,BLK-2,2): pygame.draw.line(srf,C3,(x+i,y+2),(x+i,y+BLK-3))
    elif s==2:
        pygame.draw.rect(srf,C3,(x,y,BLK,BLK),1)
        pygame.draw.rect(srf,C1,(x+1,y+1,BLK-2,BLK-2))
        pygame.draw.rect(srf,C3,(x+4,y+4,BLK-8,BLK-8))
    elif s==3:
        pygame.draw.rect(srf,C3,(x,y,BLK,BLK))
        pygame.draw.rect(srf,C0,(x+2,y+2,BLK-4,BLK-4))
        pygame.draw.rect(srf,C3,(x+6,y+6,BLK-12,BLK-12))

def dmini(srf,name,cx,cy,bs=8):
    bl=ROT[name][0]; xs=[b[0] for b in bl]; ys=[b[1] for b in bl]
    ox=cx-(max(xs)-min(xs)+1)*bs//2; oy=cy-(max(ys)-min(ys)+1)*bs//2
    for bx,by in bl:
        tx=ox+(bx-min(xs))*bs; ty=oy+(by-min(ys))*bs
        pygame.draw.rect(srf,C3,(tx,ty,bs,bs))
        pygame.draw.rect(srf,C1,(tx+1,ty+1,bs-2,bs-2))

# ====================== GAME ENGINE ======================
class Game:
    def __init__(self):
        self.board=[[None]*COLS for _ in range(ROWS)]
        self.score=0;self.lines=0;self.level=0;self.slevel=0;self.high=10000
        self.running=False;self.paused=False;self.gameover=False
        self.go_anim=False;self.go_row=ROWS-1
        self.pname='';self.pcol=0;self.prow=0;self.rot=0;self.nxt=''
        self.stats={n:0 for n in PNAMES}
        self.das_ct=0;self.das_dir=0;self.grav_ct=0
        self.sdrop=False;self.are_ct=0;self.clines=[];self.cl_timer=0

    def _rng(self): return random.choice(PNAMES)

    def start(self,sl=0):
        self.__init__(); self.slevel=sl; self.level=sl
        self.running=True; self.nxt=self._rng(); self._spawn()

    def _grav(self): return GRAV.get(min(self.level,20),3)

    def _spawn(self):
        self.pname=self.nxt; self.nxt=self._rng(); self.rot=0
        self.stats[self.pname]+=1
        bl=ROT[self.pname][0]; xs=[b[0] for b in bl]
        self.pcol=(COLS-(max(xs)-min(xs)+1))//2-min(xs)
        self.prow=-1 if self.pname=='I' else 0; self.grav_ct=0
        if not self._valid(self.pcol,self.prow,self.rot): self._die()

    def _blocks(self,c=None,r=None,ro=None):
        c=self.pcol if c is None else c
        r=self.prow if r is None else r
        ro=self.rot if ro is None else ro
        st=ROT[self.pname][ro%len(ROT[self.pname])]
        return [(c+bx,r+by) for bx,by in st]

    def _valid(self,c,r,ro):
        for x,y in self._blocks(c,r,ro):
            if x<0 or x>=COLS or y>=ROWS: return False
            if y>=0 and self.board[y][x] is not None: return False
        return True

    def _move(self,dx):
        if self._valid(self.pcol+dx,self.prow,self.rot): self.pcol+=dx; return True
        return False

    def _rotate(self):
        if self.pname=='O': return False
        nr=(self.rot+1)%len(ROT[self.pname])
        if self._valid(self.pcol,self.prow,nr): self.rot=nr; return True
        return False

    def _lock(self):
        for x,y in self._blocks():
            if 0<=y<ROWS and 0<=x<COLS: self.board[y][x]=self.pname

    def _check(self):
        full=[r for r in range(ROWS) if all(c is not None for c in self.board[r])]
        if full: self.clines=full; self.cl_timer=20; return True
        return False

    def _doclear(self):
        n=len(self.clines); self.score+=LSCORES.get(n,0)*(self.level+1)
        for r in sorted(self.clines,reverse=True):
            self.board.pop(r); self.board.insert(0,[None]*COLS)
        self.lines+=n
        if self.lines>=(self.slevel+1)*10 and self.lines>=max(100,self.slevel*10-50):
            self.level=self.slevel+(self.lines-max(100,self.slevel*10-50))//10+1
        self.clines=[]

    def _die(self):
        self.running=False; self.go_anim=True; self.go_row=ROWS-1
        if self.score>self.high: self.high=self.score

    def frame(self):
        if not self.running or self.paused: return []
        ev=[]
        if self.go_anim:
            if self.go_row>=0:
                for c in range(COLS): self.board[self.go_row][c]='O'
                self.go_row-=1
            else:
                self.go_anim=False; self.gameover=True; ev.append('gameover')
            return ev
        if self.clines:
            self.cl_timer-=1
            if self.cl_timer<=0: self._doclear(); self.are_ct=ARE_FR
            return ev
        if self.are_ct>0:
            self.are_ct-=1
            if self.are_ct<=0: self._spawn()
            return ev
        if self.das_dir!=0:
            self.das_ct+=1
            if self.das_ct==1:
                if self._move(self.das_dir): ev.append('move')
            elif self.das_ct>=DAS_INIT:
                if (self.das_ct-DAS_INIT)%DAS_REP==0:
                    if self._move(self.das_dir): ev.append('move')
        spd=2 if self.sdrop else self._grav()
        self.grav_ct+=1
        if self.grav_ct>=spd:
            self.grav_ct=0
            if self._valid(self.pcol,self.prow+1,self.rot):
                self.prow+=1
                if self.sdrop: self.score+=1
            else:
                self._lock(); ev.append('land')
                if self._check():
                    ev.append('tetris' if len(self.clines)==4 else 'clear')
                else:
                    self.are_ct=ARE_FR
        return ev

# ====================== APP ======================
class App:
    def __init__(self):
        pygame.init()
        self.aok=False
        try:
            pygame.mixer.init(frequency=SR,size=-16,channels=2,buffer=2048)
            self.aok=True
        except: print("No audio. Running silent.")

        self.scr=pygame.display.set_mode((SW,SH))
        pygame.display.set_caption("AC's TETRIS — GB Edition")
        self.clk=pygame.time.Clock()
        self.ft=_font(30); self.fm=_font(18); self.fs=_font(14); self.fh=_font(16)

        self.osts={}; self.sfx={}
        if self.aok:
            print("Synthesizing Full OSTs — 160 BPM, 25% duty, GB articulation…")
            self.osts['A']=_build_ost(MEL_A)
            self.osts['B']=_build_ost(MEL_B)
            self.osts['C']=_build_ost(MEL_C)
            for n in ['move','rotate','land','clear','tetris','gameover','menu']:
                self.sfx[n]=_build_sfx(n)
            print("Ready.")

        self.mtype='A'
        self.mch=pygame.mixer.Channel(0) if self.aok else None
        self.sch=pygame.mixer.Channel(1) if self.aok else None
        self.state='menu'; self.mi=0; self.lsel=0; self.g=Game()

    def _psfx(self,n):
        if self.aok and self.sch and n in self.sfx and self.sfx[n]:
            self.sch.play(self.sfx[n])

    def _mstart(self):
        # game-only: loops parameter set to -1 loops forever automatically
        if self.aok and self.mch and self.mtype in self.osts:
            self.mch.play(self.osts[self.mtype],loops=-1)

    def _mstop(self):
        if self.mch: self.mch.stop()

    def run(self):
        while True:
            for e in pygame.event.get():
                if e.type==pygame.QUIT: pygame.quit(); sys.exit()
                self._evt(e)
            self._upd(); self._drw()
            pygame.display.flip(); self.clk.tick(FPS)

    def _evt(self,e):
        g=self.g
        if e.type==pygame.KEYUP and self.state=='game':
            if e.key==pygame.K_LEFT  and g.das_dir==-1: g.das_dir=0;g.das_ct=0
            elif e.key==pygame.K_RIGHT and g.das_dir==1: g.das_dir=0;g.das_ct=0
            elif e.key==pygame.K_DOWN: g.sdrop=False
            return
        if e.type!=pygame.KEYDOWN: return
        k=e.key

        if self.state=='menu':
            if   k==pygame.K_UP:   self.mi=max(0,self.mi-1);self._psfx('menu')
            elif k==pygame.K_DOWN: self.mi=min(1,self.mi+1);self._psfx('menu')
            elif k in(pygame.K_LEFT,pygame.K_RIGHT) and self.mi==1:
                opts=['A','B','C','OFF']
                idx=(opts.index(self.mtype)+(1 if k==pygame.K_RIGHT else -1))%len(opts)
                self.mtype=opts[idx]; self._psfx('menu')
            elif k in(pygame.K_RETURN,pygame.K_SPACE) and self.mi==0:
                self.state='lvl'; self._psfx('menu')

        elif self.state=='lvl':
            if   k==pygame.K_LEFT:  self.lsel=max(0,self.lsel-1);self._psfx('menu')
            elif k==pygame.K_RIGHT: self.lsel=min(9,self.lsel+1);self._psfx('menu')
            elif k==pygame.K_UP:    self.lsel=max(0,self.lsel-5);self._psfx('menu')
            elif k==pygame.K_DOWN:  self.lsel=min(9,self.lsel+5);self._psfx('menu')
            elif k in(pygame.K_RETURN,pygame.K_SPACE):
                self.state='game'; g.start(self.lsel)
                if self.mtype!='OFF': self._mstart()   # ← music starts here only
            elif k==pygame.K_ESCAPE:
                self.state='menu'; self._mstop(); self._psfx('menu')

        elif self.state=='game':
            if g.gameover and not g.go_anim:
                if k==pygame.K_RETURN: self.state='menu'; self._mstop()
                return
            if k in(pygame.K_p,pygame.K_ESCAPE):
                if g.running:
                    g.paused=not g.paused
                    if g.paused: self._mstop()
                    elif self.mtype!='OFF': self._mstart()
                return
            if g.paused or not g.running or g.are_ct>0 or g.clines: return
            if   k==pygame.K_LEFT:            g.das_dir=-1;g.das_ct=0
            elif k==pygame.K_RIGHT:           g.das_dir= 1;g.das_ct=0
            elif k==pygame.K_DOWN:            g.sdrop=True
            elif k in(pygame.K_UP,pygame.K_x):
                if g._rotate(): self._psfx('rotate')

    def _upd(self):
        if self.state=='game':
            for ev in self.g.frame():
                self._psfx(ev)
                if ev=='gameover': self._mstop()

    def _drw(self):
        self.scr.fill(C0)
        pygame.draw.rect(self.scr,C2,(0,0,SW,SH),8)
        pygame.draw.rect(self.scr,C1,(8,8,SW-16,SH-16),4)
        if   self.state=='menu': self._drw_menu()
        elif self.state=='lvl':  self._drw_lvl()
        elif self.state=='game': self._drw_game()

    def _drw_menu(self):
        dtc(self.scr,"TETRIS",_font(50),C3,60)
        dtc(self.scr,"1989 Nintendo",self.fs,C3,120)
        dtc(self.scr,"> PLAY <" if self.mi==0 else "  PLAY  ",self.ft,C3,200)
        dtc(self.scr,
            f"> MUSIC: {self.mtype} <" if self.mi==1 else f"  MUSIC: {self.mtype}  ",
            self.ft,C3,250)

    def _drw_lvl(self):
        dtc(self.scr,"A-TYPE",self.ft,C3,50); dtc(self.scr,"LEVEL",self.fm,C3,110)
        bx,by=SW//2-125,150
        for i in range(10):
            x=bx+(i%5)*50; y=by+(i//5)*50
            if i==self.lsel:
                pygame.draw.rect(self.scr,C3,(x,y,40,40))
                t=self.fm.render(str(i),True,C0)
            else:
                pygame.draw.rect(self.scr,C3,(x,y,40,40),2)
                t=self.fm.render(str(i),True,C3)
            self.scr.blit(t,(x+20-t.get_width()//2,y+10))

    def _drw_game(self):
        g=self.g
        pygame.draw.rect(self.scr,C2,(BRD_X-4,BRD_Y-4,COLS*BLK+8,ROWS*BLK+8))
        pygame.draw.rect(self.scr,C0,(BRD_X,BRD_Y,COLS*BLK,ROWS*BLK))
        for r in range(ROWS):
            for c in range(COLS):
                if g.board[r][c]:
                    x=BRD_X+c*BLK; y=BRD_Y+r*BLK
                    if r in g.clines and (pygame.time.get_ticks()//80)%2==0:
                        pygame.draw.rect(self.scr,C0,(x,y,BLK,BLK))
                    else: dblk(self.scr,x,y,g.board[r][c])
        if g.running and not g.paused and g.are_ct==0 and not g.clines:
            for bx,by in g._blocks():
                if 0<=by<ROWS: dblk(self.scr,BRD_X+bx*BLK,BRD_Y+by*BLK,g.pname)

        lx=BRD_X-120; rx=BRD_X+COLS*BLK+20
        dtc(self.scr,"STATISTICS",self.fs,C3,BRD_Y,lx+50)
        for i,name in enumerate(PNAMES):
            dmini(self.scr,name,lx+30,BRD_Y+35+i*35)
            st=self.fs.render(f"{g.stats[name]:03d}",True,C3)
            self.scr.blit(st,(lx+60,BRD_Y+28+i*35))

        dtc(self.scr,"SCORE",self.fs,C3,BRD_Y+10, rx+40)
        st=self.fh.render(f"{g.score:06d}",True,C3)
        self.scr.blit(st,(rx+40-st.get_width()//2,BRD_Y+30))
        dtc(self.scr,"LEVEL",self.fs,C3,BRD_Y+70, rx+40)
        lt=self.fh.render(f"{g.level:02d}",True,C3)
        self.scr.blit(lt,(rx+40-lt.get_width()//2,BRD_Y+90))
        dtc(self.scr,"LINES",self.fs,C3,BRD_Y+130,rx+40)
        lnt=self.fh.render(f"{g.lines:03d}",True,C3)
        self.scr.blit(lnt,(rx+40-lnt.get_width()//2,BRD_Y+150))

        pygame.draw.rect(self.scr,C2,(rx,BRD_Y+200,80,80),2)
        dtc(self.scr,"NEXT",self.fs,C3,BRD_Y+210,rx+40)
        if g.nxt: dmini(self.scr,g.nxt,rx+40,BRD_Y+250,bs=10)

        if g.paused:
            pygame.draw.rect(self.scr,C0,(SW//2-60,SH//2-20,120,40))
            pygame.draw.rect(self.scr,C3,(SW//2-60,SH//2-20,120,40),4)
            dtc(self.scr,"PAUSE",self.fm,C3,SH//2-10)
        if g.gameover and not g.go_anim:
            pygame.draw.rect(self.scr,C0,(SW//2-80,SH//2-30,160,60))
            pygame.draw.rect(self.scr,C3,(SW//2-80,SH//2-30,160,60),4)
            dtc(self.scr,"GAME OVER",  self.fm,C3,SH//2-20)
            dtc(self.scr,"Press ENTER",self.fs,C3,SH//2+5)

if __name__=='__main__':
    App().run()
