#!/usr/bin/env python3.14
"""
AC's Ultra!TETRIS - Game Boy Edition (60 FPS)
Fully synthesized assets (files = off).
Imported all OSTs (A-Type, B-Type, C-Type) & GB Graphics.
Resolution: 600x400
Speed/Gravity: Authentic Game Boy Curve

Modifications:
- Music now plays only when a game level is started (not in menus).
- The full song loops continuously during gameplay.
- Pausing stops music; unpausing resumes.
- Music stops on game over and when returning to menu.
- A-Type OST expanded to full loop length.
"""

import math
print("python3.14")
import pygame
import sys
import random
import struct
import array

# ====================== CONSTANTS ======================
SW, SH = 600, 400
COLS, ROWS = 10, 20
BLK = 16
FPS = 60
BRD_X = SW // 2 - (COLS * BLK) // 2
BRD_Y = SH // 2 - (ROWS * BLK) // 2 + 8

# Game Boy Palette (Olive Green)
C0 = (155, 188, 15)  # Lightest (BG)
C1 = (139, 172, 15)  # Light
C2 = (48, 98, 48)    # Dark
C3 = (15, 56, 15)    # Darkest

PNAMES = ['T', 'J', 'Z', 'O', 'S', 'L', 'I']

# ====================== NRS ROTATION ======================
ROT = {
    'I': [[(0,1),(1,1),(2,1),(3,1)], [(2,0),(2,1),(2,2),(2,3)]],
    'O': [[(0,0),(1,0),(0,1),(1,1)]],
    'T': [[(0,0),(1,0),(2,0),(1,1)], [(1,0),(0,1),(1,1),(1,2)], [(1,0),(0,1),(1,1),(2,1)], [(1,0),(1,1),(2,1),(1,2)]],
    'J': [[(0,0),(1,0),(2,0),(2,1)], [(1,0),(1,1),(0,2),(1,2)], [(0,0),(0,1),(1,1),(2,1)], [(1,0),(2,0),(1,1),(1,2)]],
    'L': [[(0,0),(1,0),(2,0),(0,1)], [(0,0),(1,0),(1,1),(1,2)], [(2,0),(0,1),(1,1),(2,1)], [(1,0),(1,1),(1,2),(2,2)]],
    'S': [[(1,0),(2,0),(0,1),(1,1)], [(0,0),(0,1),(1,1),(1,2)]],
    'Z': [[(0,0),(1,0),(1,1),(2,1)], [(1,0),(0,1),(1,1),(0,2)]]
}

# ====================== GB GRAVITY CURVE ======================
# Frames per drop at 59.7 FPS for authentic GB speed
GRAV = {
    0: 53, 1: 49, 2: 45, 3: 41, 4: 37, 5: 33, 6: 28, 7: 22, 8: 17, 9: 11,
    10: 10, 11: 9, 12: 8, 13: 7, 14: 6, 15: 6, 16: 5, 17: 5, 18: 4, 19: 4, 20: 3
}

DAS_INIT = 24
DAS_REP  = 9
ARE_FR   = 2  # Very short spawn delay for GB feel
LSCORES  = {1: 40, 2: 100, 3: 300, 4: 1200}

# ====================== AUDIO ENGINE ======================
SR = 44100

def _pulse(freq, dur, duty=0.5, vol=0.3, decay=0.1):
    n = int(SR * dur)
    out = array.array('h')
    for i in range(n):
        if freq <= 0:
            out.append(0)
            continue
        t = i / SR
        w = 1.0 if (freq * t) % 1.0 < duty else -1.0
        v = max(0.0, vol - decay * t) if decay > 0 else vol
        out.append(int(max(-32767, min(32767, w * v * 32767))))
    return out

def _wave(freq, dur, vol=0.25):
    n = int(SR * dur)
    out = array.array('h')
    for i in range(n):
        if freq <= 0:
            out.append(0)
            continue
        t = i / SR
        w = math.sin(2 * math.pi * freq * t)
        out.append(int(max(-32767, min(32767, w * vol * 32767))))
    return out

def _noise(dur, vol=0.15):
    n = int(SR * dur)
    out = array.array('h')
    for i in range(n):
        v = vol * max(0.0, 1.0 - (i / n))
        w = random.choice([-1.0, 1.0])
        out.append(int(max(-32767, min(32767, w * v * 32767))))
    return out

def _snd(s):
    return pygame.mixer.Sound(buffer=struct.pack(f'<{len(s)}h', *s))

def _mix(*arrs):
    ml = max(len(a) for a in arrs)
    m = array.array('h', [0] * ml)
    for a in arrs:
        for i in range(len(a)):
            m[i] = int(max(-32767, min(32767, m[i] + a[i])))
    return m

NF = {
    'G3':196.0, 'A3':220.0, 'B3':246.9, 'C4':261.6, 'D4':293.7, 'E4':329.6,
    'F4':349.2, 'F#4':370.0, 'G4':392.0, 'G#4':415.3, 'A4':440.0, 'A#4':466.2,
    'B4':493.9, 'C5':523.3, 'C#5':554.4, 'D5':587.3, 'D#5':622.3, 'E5':659.3,
    'F5':698.5, 'F#5':740.0, 'G5':784.0, 'R':0
}

BT = 0.15

# A-TYPE: Korobeiniki (Full Loop Length)
MEL_A_SEGMENT = [
    ('E5',2),('B4',1),('C5',1),('D5',2),('C5',1),('B4',1),
    ('A4',2),('A4',1),('C5',1),('E5',2),('D5',1),('C5',1),
    ('B4',3),('C5',1),('D5',2),('E5',2),('C5',2),('A4',2),('A4',2),('R',2)
]
# Doubled to match the original OST loop length (approx 30s)
MEL_A = MEL_A_SEGMENT * 2

# B-TYPE: Generic Russian/Classical mix GB style
MEL_B = [
    ('E5',1),('E5',1),('E5',1),('C5',1),('D5',1),('E5',1),('D5',1),('C5',1),
    ('B4',1),('B4',1),('A4',2),('G4',2),('F4',2),('E4',2),('R',2)
]

# C-TYPE: Bach French Suite
MEL_C = [
    ('B4',1),('A4',1),('B4',1),('C5',1),('D5',2),('G4',2),('G4',2),
    ('C5',1),('B4',1),('C5',1),('D5',1),('E5',2),('G4',2),('G4',2)
]

def _build_ost(m_data):
    m = array.array('h')
    # Play the passed data once (data is already full length)
    for note, d in m_data:
        m.extend(_pulse(NF.get(note, 0), d * BT, 0.5, 0.3, 0.1))

    b = array.array('h')
    for note, d in m_data:
        bass_note = note[:-1] + str(int(note[-1])-1) if note != 'R' else 'R'
        b.extend(_wave(NF.get(bass_note, 0), d * BT, 0.25))

    return _snd(_mix(m, b))

def _build_sfx(name):
    if name == 'move':    return _snd(_pulse(880, .025, .5, .1, decay=1.0))
    if name == 'rotate':  return _snd(_pulse(1200, .03, .5, .1, decay=2.0))
    if name == 'land':    return _snd(_mix(_pulse(150, .05, .5, .1), _noise(.05, .1)))
    if name == 'clear':   return _snd(_pulse(659, .15, .5, .15, decay=1.0))
    if name == 'tetris':
        s = array.array('h')
        for f in [523, 659, 784, 1047]: s.extend(_pulse(f, .08, .5, .15))
        return _snd(s)
    if name == 'gameover':return _snd(_pulse(200, .5, .5, .2, decay=1.0))
    if name == 'menu':    return _snd(_pulse(740, .03, .5, .1))
    return None

# ====================== GRAPHICS / DRAWING ======================
def _font(sz):
    return pygame.font.SysFont('couriernew', sz, bold=True)

def dtc(srf, txt, f, c, y, cx=None):
    r = f.render(txt, True, c)
    srf.blit(r, ((cx or SW // 2) - r.get_width() // 2, y))

# Game Boy specific block rendering
def dblk(srf, x, y, name, is_empty=False):
    if is_empty:
        pygame.draw.rect(srf, C0, (x, y, BLK, BLK))
        return

    # GB Style Textures
    P_STYLE = {'T': 1, 'J': 0, 'Z': 2, 'O': 3, 'S': 2, 'L': 0, 'I': 1}
    style = P_STYLE.get(name, 0)

    # Base background for block
    pygame.draw.rect(srf, C0, (x, y, BLK, BLK))

    if style == 0:
        # Solid dark with light border
        pygame.draw.rect(srf, C3, (x, y, BLK, BLK))
        pygame.draw.rect(srf, C1, (x+1, y+1, BLK-2, BLK-2))
        pygame.draw.rect(srf, C3, (x+3, y+3, BLK-6, BLK-6))
    elif style == 1:
        # Checkered / Striped
        pygame.draw.rect(srf, C3, (x, y, BLK, BLK), 1)
        pygame.draw.rect(srf, C2, (x+1, y+1, BLK-2, BLK-2))
        for i in range(2, BLK-2, 2):
            pygame.draw.line(srf, C3, (x+i, y+2), (x+i, y+BLK-3))
    elif style == 2:
        # Dotted
        pygame.draw.rect(srf, C3, (x, y, BLK, BLK), 1)
        pygame.draw.rect(srf, C1, (x+1, y+1, BLK-2, BLK-2))
        pygame.draw.rect(srf, C3, (x+4, y+4, BLK-8, BLK-8))
    elif style == 3:
        # Hollow O-style
        pygame.draw.rect(srf, C3, (x, y, BLK, BLK))
        pygame.draw.rect(srf, C0, (x+2, y+2, BLK-4, BLK-4))
        pygame.draw.rect(srf, C3, (x+6, y+6, BLK-12, BLK-12))

def dmini(srf, name, cx, cy, bs=8):
    bl = ROT[name][0]
    xs = [b[0] for b in bl]
    ys = [b[1] for b in bl]
    w = (max(xs) - min(xs) + 1) * bs
    h = (max(ys) - min(ys) + 1) * bs
    ox = cx - w // 2
    oy = cy - h // 2
    for bx, by in bl:
        tx = ox + (bx - min(xs)) * bs
        ty = oy + (by - min(ys)) * bs

        # Draw a miniature block
        pygame.draw.rect(srf, C3, (tx, ty, bs, bs))
        pygame.draw.rect(srf, C1, (tx+1, ty+1, bs-2, bs-2))

# ====================== TETRIS ENGINE ======================
class Game:
    def __init__(self):
        self.board = [[None]*COLS for _ in range(ROWS)]
        self.score = 0
        self.lines = 0
        self.level = 0
        self.slevel = 0
        self.high = 10000
        self.running = False
        self.paused = False
        self.gameover = False
        self.go_anim = False
        self.go_row = ROWS - 1
        self.pname = ''
        self.pcol = 0
        self.prow = 0
        self.rot = 0
        self.nxt = ''
        self.stats = {n: 0 for n in PNAMES}
        self.das_ct = 0
        self.das_dir = 0
        self.grav_ct = 0
        self.sdrop = False
        self.are_ct = 0
        self.clines = []
        self.cl_timer = 0

    def _rng(self):
        return random.choice(PNAMES)

    def start(self, sl=0):
        self.__init__()
        self.slevel = sl
        self.level = sl
        self.running = True
        self.nxt = self._rng()
        self._spawn()

    def _grav(self):
        lv = min(self.level, 20)
        return GRAV.get(lv, 3)

    def _spawn(self):
        self.pname = self.nxt
        self.nxt = self._rng()
        self.rot = 0
        self.stats[self.pname] += 1
        bl = ROT[self.pname][0]
        xs = [b[0] for b in bl]
        self.pcol = (COLS - (max(xs) - min(xs) + 1)) // 2 - min(xs)
        self.prow = -1 if self.pname == 'I' else 0
        self.grav_ct = 0
        if not self._valid(self.pcol, self.prow, self.rot):
            self._die()

    def _blocks(self, c=None, r=None, ro=None):
        if c is None: c = self.pcol
        if r is None: r = self.prow
        if ro is None: ro = self.rot
        st = ROT[self.pname][ro % len(ROT[self.pname])]
        return [(c + bx, r + by) for bx, by in st]

    def _valid(self, c, r, ro):
        for x, y in self._blocks(c, r, ro):
            if x < 0 or x >= COLS or y >= ROWS:
                return False
            if y >= 0 and self.board[y][x] is not None:
                return False
        return True

    def _move(self, dx):
        if self._valid(self.pcol + dx, self.prow, self.rot):
            self.pcol += dx
            return True
        return False

    def _rotate(self):
        if self.pname == 'O': return False
        nr = (self.rot + 1) % len(ROT[self.pname])
        if self._valid(self.pcol, self.prow, nr):
            self.rot = nr
            return True
        return False

    def _lock(self):
        for x, y in self._blocks():
            if 0 <= y < ROWS and 0 <= x < COLS:
                self.board[y][x] = self.pname

    def _check(self):
        full = [r for r in range(ROWS) if all(c is not None for c in self.board[r])]
        if full:
            self.clines = full
            self.cl_timer = 20
            return True
        return False

    def _doclear(self):
        n = len(self.clines)
        self.score += LSCORES.get(n, 0) * (self.level + 1)
        for r in sorted(self.clines, reverse=True):
            self.board.pop(r)
            self.board.insert(0, [None] * COLS)

        ol = self.level
        self.lines += n
        # GB Level up logic
        if self.lines >= (self.slevel + 1) * 10 and self.lines >= max(100, (self.slevel * 10 - 50)):
            self.level = self.slevel + (self.lines - max(100, self.slevel * 10 - 50)) // 10 + 1

        self.clines = []
        return self.level > ol

    def _die(self):
        self.running = False
        self.go_anim = True
        self.go_row = ROWS - 1
        if self.score > self.high:
            self.high = self.score

    def frame(self):
        if not self.running or self.paused:
            return []
        ev = []

        if self.go_anim:
            if self.go_row >= 0:
                for c in range(COLS):
                    self.board[self.go_row][c] = 'O'
                self.go_row -= 1
            else:
                self.go_anim = False
                self.gameover = True
                ev.append('gameover')
            return ev

        if self.clines:
            self.cl_timer -= 1
            if self.cl_timer <= 0:
                self._doclear()
                self.are_ct = ARE_FR
            return ev

        if self.are_ct > 0:
            self.are_ct -= 1
            if self.are_ct <= 0:
                self._spawn()
            return ev

        if self.das_dir != 0:
            self.das_ct += 1
            if self.das_ct == 1:
                if self._move(self.das_dir): ev.append('move')
            elif self.das_ct >= DAS_INIT:
                if (self.das_ct - DAS_INIT) % DAS_REP == 0:
                    if self._move(self.das_dir): ev.append('move')

        spd = 2 if self.sdrop else self._grav()
        self.grav_ct += 1
        if self.grav_ct >= spd:
            self.grav_ct = 0
            if self._valid(self.pcol, self.prow + 1, self.rot):
                self.prow += 1
                if self.sdrop: self.score += 1
            else:
                self._lock()
                ev.append('land')
                if self._check():
                    ev.append('tetris' if len(self.clines) == 4 else 'clear')
                else:
                    self.are_ct = ARE_FR
        return ev

# ====================== APP / GUI ======================
class App:
    def __init__(self):
        pygame.init()
        self.aok = False
        try:
            pygame.mixer.init(frequency=SR, size=-16, channels=2, buffer=2048)
            self.aok = True
        except Exception:
            print("No audio device. Running silent.")

        self.scr = pygame.display.set_mode((SW, SH))
        pygame.display.set_caption("AC'S Tetris v0")  # <-- Renamed here
        self.clk = pygame.time.Clock()

        self.ft = _font(30)
        self.fm = _font(18)
        self.fs = _font(14)
        self.fh = _font(16)

        self.osts = {}
        self.sfx = {}
        if self.aok:
            print("Synthesizing GB OSTs...")
            self.osts['A'] = _build_ost(MEL_A)
            self.osts['B'] = _build_ost(MEL_B)
            self.osts['C'] = _build_ost(MEL_C)
            for n in ['move','rotate','land','clear','tetris','gameover','menu']:
                self.sfx[n] = _build_sfx(n)

        self.mtype = 'A'  # A, B, C, OFF
        self.mch = pygame.mixer.Channel(0) if self.aok else None
        self.sch = pygame.mixer.Channel(1) if self.aok else None

        self.state = 'menu'
        self.mi = 0
        self.lsel = 0
        self.g = Game()

    def _psfx(self, n):
        if self.aok and self.sch and n in self.sfx and self.sfx[n]:
            self.sch.play(self.sfx[n])

    def _mstart(self):
        if self.aok and self.mch and self.mtype in self.osts:
            self.mch.play(self.osts[self.mtype], loops=-1)

    def _mstop(self):
        if self.mch: self.mch.stop()

    def run(self):
        while True:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                self._evt(e)
            self._upd()
            self._drw()
            pygame.display.flip()
            self.clk.tick(FPS)

    def _evt(self, e):
        g = self.g
        if e.type == pygame.KEYUP and self.state == 'game':
            if e.key == pygame.K_LEFT and g.das_dir == -1:
                g.das_dir = 0; g.das_ct = 0
            elif e.key == pygame.K_RIGHT and g.das_dir == 1:
                g.das_dir = 0; g.das_ct = 0
            elif e.key == pygame.K_DOWN:
                g.sdrop = False
            return

        if e.type != pygame.KEYDOWN: return
        k = e.key

        if self.state == 'menu':
            if k == pygame.K_UP: self.mi = max(0, self.mi - 1); self._psfx('menu')
            elif k == pygame.K_DOWN: self.mi = min(1, self.mi + 1); self._psfx('menu')
            elif k in (pygame.K_LEFT, pygame.K_RIGHT) and self.mi == 1:
                opts = ['A', 'B', 'C', 'OFF']
                idx = opts.index(self.mtype)
                idx = (idx + (1 if k == pygame.K_RIGHT else -1)) % len(opts)
                self.mtype = opts[idx]
                self._psfx('menu')
            elif k in (pygame.K_RETURN, pygame.K_SPACE) and self.mi == 0:
                self.state = 'lvl'
                self._psfx('menu')

        elif self.state == 'lvl':
            if k == pygame.K_LEFT: self.lsel = max(0, self.lsel - 1); self._psfx('menu')
            elif k == pygame.K_RIGHT: self.lsel = min(9, self.lsel + 1); self._psfx('menu')
            elif k == pygame.K_UP: self.lsel = max(0, self.lsel - 5); self._psfx('menu')
            elif k == pygame.K_DOWN: self.lsel = min(9, self.lsel + 5); self._psfx('menu')
            elif k in (pygame.K_RETURN, pygame.K_SPACE):
                self.state = 'game'
                g.start(self.lsel)
                if self.mtype != 'OFF':
                    self._mstart()
            elif k == pygame.K_ESCAPE:
                self.state = 'menu'; self._psfx('menu')

        elif self.state == 'game':
            if g.gameover and not g.go_anim:
                if k == pygame.K_RETURN:
                    self.state = 'menu'
                    self._mstop()
                return
            if k in (pygame.K_p, pygame.K_ESCAPE):
                if g.running:
                    g.paused = not g.paused
                    if g.paused:
                        self._mstop()
                    else:
                        if self.mtype != 'OFF':
                            self._mstart()
                return
            if g.paused or not g.running or g.are_ct > 0 or g.clines: return

            if k == pygame.K_LEFT:
                g.das_dir = -1; g.das_ct = 0
            elif k == pygame.K_RIGHT:
                g.das_dir = 1; g.das_ct = 0
            elif k == pygame.K_DOWN:
                g.sdrop = True
            elif k in (pygame.K_UP, pygame.K_x):
                if g._rotate(): self._psfx('rotate')

    def _upd(self):
        if self.state == 'game':
            for ev in self.g.frame():
                self._psfx(ev)
                if ev == 'gameover':
                    self._mstop()

    def _drw(self):
        self.scr.fill(C0)

        # Draw "GAME BOY" frame
        pygame.draw.rect(self.scr, C2, (0, 0, SW, SH), 8)
        pygame.draw.rect(self.scr, C1, (8, 8, SW-16, SH-16), 4)

        if self.state == 'menu':
            dtc(self.scr, "TETRIS", _font(50), C3, 60)
            dtc(self.scr, "1989 Nintendo", self.fs, C3, 120)

            opt_play = "> PLAY <" if self.mi == 0 else "  PLAY  "
            dtc(self.scr, opt_play, self.ft, C3, 200)

            opt_mus = f"> MUSIC: {self.mtype} <" if self.mi == 1 else f"  MUSIC: {self.mtype}  "
            dtc(self.scr, opt_mus, self.ft, C3, 250)

        elif self.state == 'lvl':
            dtc(self.scr, "A-TYPE", self.ft, C3, 50)
            dtc(self.scr, "LEVEL", self.fm, C3, 110)

            bx, by = SW//2 - 125, 150
            for i in range(10):
                x = bx + (i % 5) * 50
                y = by + (i // 5) * 50
                if i == self.lsel:
                    pygame.draw.rect(self.scr, C3, (x, y, 40, 40))
                    t = self.fm.render(str(i), True, C0)
                else:
                    pygame.draw.rect(self.scr, C3, (x, y, 40, 40), 2)
                    t = self.fm.render(str(i), True, C3)
                self.scr.blit(t, (x + 20 - t.get_width()//2, y + 10))

        elif self.state == 'game':
            self._drw_game()

    def _drw_game(self):
        g = self.g

        # Board Border
        pygame.draw.rect(self.scr, C2, (BRD_X - 4, BRD_Y - 4, COLS*BLK + 8, ROWS*BLK + 8))
        pygame.draw.rect(self.scr, C0, (BRD_X, BRD_Y, COLS*BLK, ROWS*BLK))

        for r in range(ROWS):
            for c in range(COLS):
                if g.board[r][c]:
                    x = BRD_X + c * BLK
                    y = BRD_Y + r * BLK
                    if r in g.clines and (pygame.time.get_ticks() // 80) % 2 == 0:
                        pygame.draw.rect(self.scr, C0, (x, y, BLK, BLK))
                    else:
                        dblk(self.scr, x, y, g.board[r][c])

        if g.running and not g.paused and g.are_ct == 0 and not g.clines:
            for bx, by in g._blocks():
                if 0 <= by < ROWS:
                    dblk(self.scr, BRD_X + bx*BLK, BRD_Y + by*BLK, g.pname)

        # UI Panels
        lx = BRD_X - 120
        rx = BRD_X + COLS*BLK + 20

        # Stats
        dtc(self.scr, "STATISTICS", self.fs, C3, BRD_Y, lx + 50)
        for i, name in enumerate(PNAMES):
            dmini(self.scr, name, lx + 30, BRD_Y + 35 + i * 35)
            st = self.fs.render(f"{g.stats[name]:03d}", True, C3)
            self.scr.blit(st, (lx + 60, BRD_Y + 28 + i * 35))

        # Score / Next
        dtc(self.scr, "SCORE", self.fs, C3, BRD_Y + 10, rx + 40)
        st = self.fh.render(f"{g.score:06d}", True, C3)
        self.scr.blit(st, (rx + 40 - st.get_width()//2, BRD_Y + 30))

        dtc(self.scr, "LEVEL", self.fs, C3, BRD_Y + 70, rx + 40)
        lt = self.fh.render(f"{g.level:02d}", True, C3)
        self.scr.blit(lt, (rx + 40 - lt.get_width()//2, BRD_Y + 90))

        dtc(self.scr, "LINES", self.fs, C3, BRD_Y + 130, rx + 40)
        lnt = self.fh.render(f"{g.lines:03d}", True, C3)
        self.scr.blit(lnt, (rx + 40 - lnt.get_width()//2, BRD_Y + 150))

        pygame.draw.rect(self.scr, C2, (rx, BRD_Y + 200, 80, 80), 2)
        dtc(self.scr, "NEXT", self.fs, C3, BRD_Y + 210, rx + 40)
        if g.nxt:
            dmini(self.scr, g.nxt, rx + 40, BRD_Y + 250, bs=10)

        if g.paused:
            pygame.draw.rect(self.scr, C0, (SW//2 - 60, SH//2 - 20, 120, 40))
            pygame.draw.rect(self.scr, C3, (SW//2 - 60, SH//2 - 20, 120, 40), 4)
            dtc(self.scr, "PAUSE", self.fm, C3, SH//2 - 10)

        if g.gameover and not g.go_anim:
            pygame.draw.rect(self.scr, C0, (SW//2 - 80, SH//2 - 30, 160, 60))
            pygame.draw.rect(self.scr, C3, (SW//2 - 80, SH//2 - 30, 160, 60), 4)
            dtc(self.scr, "GAME OVER", self.fm, C3, SH//2 - 20)
            dtc(self.scr, "Press ENTER", self.fs, C3, SH//2 + 5)

if __name__ == '__main__':
    App().run()
