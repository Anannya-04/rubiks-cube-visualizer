import pygame
import random
import sys
import time

FACE_COLORS = {
    "U": (255, 255, 255),   # White (Up)
    "D": (255, 255, 0),     # Yellow (Down)
    "F": (0, 200, 70),      # Green (Front)
    "B": (0, 85, 200),      # Blue (Back)
    "L": (255, 128, 0),     # Orange (Left)
    "R": (200, 30, 30),     # Red (Right)
}
SHADOW_COLOR = (60, 60, 60)
FACE_ORDER = ["U", "L", "F", "R", "B", "D"]
FACE_LABELS = {"U":"Up", "D":"Down", "F":"Front", "B":"Back", "L":"Left", "R":"Right"}

SOLVE_SPEED = 8  # Number of moves solved per second during animation

class Button:
    def __init__(self, rect, text, font, bg, fg, hover):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.font = font
        self.bg = bg
        self.fg = fg
        self.hover = hover
        self.hovered = False

    def draw(self, surface):
        color = self.hover if self.hovered else self.bg
        pygame.draw.rect(surface, color, self.rect, border_radius=8)
        border = self.hovered and 2 or 1
        pygame.draw.rect(surface, (50,50,60), self.rect, width=border, border_radius=8)
        text = self.font.render(self.text, True, self.fg)
        text_rect = text.get_rect(center=self.rect.center)
        surface.blit(text, text_rect)

    def update(self, mouse_pos):
        self.hovered = self.rect.collidepoint(mouse_pos)

    def is_clicked(self, event):
        return self.hovered and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1

class RubiksCube2D:
    def __init__(self):
        self.reset_cube()
    def reset_cube(self):
        self.faces = {face: [[face]*3 for _ in range(3)] for face in FACE_COLORS}
        self.move_history = []
        self.redo_stack = []
    def rotate_face(self, face, clockwise=True, record=True):
        f = self.faces[face]
        self.faces[face] = [list(row) for row in zip(*f[::-1])] if clockwise else [list(row) for row in zip(*f)][::-1]
        adjacent = {
            "U": [("B",0),("R",0),("F",0),("L",0)],
            "D": [("F",2),("R",2),("B",2),("L",2)],
            "F": [("U",2),("R",'col0'),("D",0),("L",'col2')],
            "B": [("U",0),("L",'col0'),("D",2),("R",'col2')],
            "L": [("U",'col0'),("F",'col0'),("D",'col0'),("B",'col2rev')],
            "R": [("U",'col2'),("B",'col0rev'),("D",'col2'),("F",'col2')],
        }
        strips = []
        for adj, idx in adjacent[face]:
            f = self.faces[adj]
            if idx == 0: strips.append(f[0][:])
            elif idx == 2: strips.append(f[2][:])
            elif idx == 'col0': strips.append([f[i][0] for i in range(3)])
            elif idx == 'col2': strips.append([f[i][2] for i in range(3)])
            elif idx == 'col2rev': strips.append([f[i][2] for i in reversed(range(3))])
            elif idx == 'col0rev': strips.append([f[i][0] for i in reversed(range(3))])
        if not clockwise: strips = strips[1:] + strips[:1]
        else: strips = strips[-1:] + strips[:-1]
        for i, (adj, idx) in enumerate(adjacent[face]):
            f = self.faces[adj]
            s = strips[i]
            if idx == 0: f[0] = s
            elif idx == 2: f[2] = s
            elif idx == 'col0': [f[r].__setitem__(0, s[r]) for r in range(3)]
            elif idx == 'col2': [f[r].__setitem__(2, s[r]) for r in range(3)]
            elif idx == 'col2rev': [f[r].__setitem__(2, s[ir]) for ir, r in enumerate(reversed(range(3)))]
            elif idx == 'col0rev': [f[r].__setitem__(0, s[ir]) for ir, r in enumerate(reversed(range(3)))]
        if record:
            self.move_history.append(face + ("" if clockwise else "'"))
            self.redo_stack.clear()
    def scramble(self, n=20):
        moves = [f for f in FACE_COLORS] + [f+"'" for f in FACE_COLORS]
        for _ in range(n):
            move = random.choice(moves)
            self.rotate_face(move[0], clockwise=not move.endswith("'"))
    def get_reverse_moves(self):
        rev = []
        for move in reversed(self.move_history):
            face = move[0]
            clockwise = move.endswith("'")
            rev.append((face, clockwise))
        return rev
    def solve_anim_moves(self):
        return self.get_reverse_moves()
    def step_solve(self):
        if not self.move_history: return False
        move = self.move_history[-1]
        face = move[0]
        clockwise = move.endswith("'")
        self.rotate_face(face, clockwise=clockwise, record=False)
        self.redo_stack.clear()
        self.move_history.pop(-1)
        return True
    def solve_all(self):
        while self.step_solve():
            pass
    def undo(self):
        if not self.move_history: return
        move = self.move_history[-1]
        face = move[0]
        clockwise = move.endswith("'")
        self.rotate_face(face, clockwise=clockwise, record=False)
        self.redo_stack.clear()
        self.move_history.pop(-1)

class Cube2DApp:
    BG = (35,37,42)
    HILITE = (240,240,180)
    SIDE_PANEL_W = 320  # Fixed width for side panel
    def __init__(self):
        pygame.init()
        self.size = self.width, self.height = 1100, 720
        self.screen = pygame.display.set_mode(self.size, pygame.RESIZABLE)
        pygame.display.set_caption("2D Rubik's Cube Visualizer - Enhanced Edition")
        self.cube = RubiksCube2D()
        self.font = pygame.font.SysFont("Segoe UI", 32, bold=True)
        self.smallfont = pygame.font.SysFont("Segoe UI", 20)
        self.tinyfont = pygame.font.SysFont("Segoe UI", 13)
        self.buttonfont = pygame.font.SysFont("Segoe UI", 22, bold=True)
        self.cube_rects = {}
        self.buttons = []
        self.solve_animating = False
        self.solve_anim_moves = []
        self.last_anim_time = 0
        self.setup_buttons()
    def setup_buttons(self):
        panelh = 110  # Bottom panel for buttons
        w = 130
        h = 48
        pad = 22
        sep = 30
        cx = self.SIDE_PANEL_W + (self.width-self.SIDE_PANEL_W)//2
        y = self.height - panelh + 25
        align = [cx-2*(w+sep//2), cx-(w+sep//2), cx, cx+(w+sep//2)]
        self.buttons = [
            Button((align[0], y, w, h), "Scramble", self.buttonfont, (70,170,80), (240,240,240), (110,200,120)),
            Button((align[1], y, w, h), "Reset",    self.buttonfont, (70,130,200), (240,240,240), (120,180,230)),
            Button((align[2], y, w, h), "Solve",    self.buttonfont, (220,150,50), (240,240,240), (250,210,90)),
            Button((align[3], y, w, h), "Undo",     self.buttonfont, (60,60,60),   (240,240,240), (150,150,150)),
        ]
    def draw_rounded_rect(self, surface, color, rect, border_radius=12, shadow=True):
        if shadow:
            srect = pygame.Rect(rect.left+4, rect.top+4, rect.width, rect.height)
            pygame.draw.rect(surface, SHADOW_COLOR, srect, border_radius=border_radius)
        pygame.draw.rect(surface, color, rect, border_radius=border_radius)
    def sticker_at_pixel(self, px, py):
        for key, rect in self.cube_rects.items():
            if rect.collidepoint(px, py): return key
        return None
    def draw_cube(self):
        surf = self.screen
        # Cube in the center, respecting side panel width and bottom buttons
        room_w = self.width - self.SIDE_PANEL_W - 80
        room_h = self.height - 160  # 110 for bottom panel + extra margin
        s = min(room_w//13, room_h//13)
        offset_x = self.SIDE_PANEL_W + 40
        offset_y = 48

        facepos = {
            "U": (offset_x+3*s, offset_y),
            "L": (offset_x, offset_y+4*s),
            "F": (offset_x+3*s, offset_y+4*s),
            "R": (offset_x+6*s, offset_y+4*s),
            "B": (offset_x+9*s, offset_y+4*s),
            "D": (offset_x+3*s, offset_y+8*s),
        }
        self.cube_rects = {}
        mx, my = pygame.mouse.get_pos()
        hovered = self.sticker_at_pixel(mx, my)
        for face in FACE_ORDER:
            fx, fy = facepos[face]
            grid = self.cube.faces[face]
            label = self.smallfont.render(FACE_LABELS[face], True, (190,190,210))
            surf.blit(label, (fx+s, fy-s//2))
            for i in range(3):
                for j in range(3):
                    color = FACE_COLORS[grid[i][j]]
                    rx = fx + j*s
                    ry = fy + i*s
                    rect = pygame.Rect(rx, ry, s, s)
                    key = (face, i, j)
                    self.cube_rects[key] = rect
                    hl = hovered==key
                    self.draw_rounded_rect(surf, color, rect, border_radius=max(8,s//7), shadow=True)
                    if hl:
                        pygame.draw.rect(surf, self.HILITE, rect, width=max(2, s//10), border_radius=max(6,s//7))
    def draw_panel_and_buttons(self):
        panelh = 110
        # Bottom panel (for buttons)
        pygame.draw.rect(self.screen, (27,27,32), (self.SIDE_PANEL_W, self.height - panelh, self.width-self.SIDE_PANEL_W, panelh))
        # Buttons
        mx, my = pygame.mouse.get_pos()
        for btn in self.buttons:
            btn.update((mx, my))
            btn.draw(self.screen)
    def draw_side_panel(self):
        # Controls/history at left in a vertical column
        panelw = self.SIDE_PANEL_W
        pygame.draw.rect(self.screen, (26,26,30), (0,0,panelw,self.height))
        x0 = 28
        y = 38
        ln = 31
        self.screen.blit(self.font.render("Rubik's Cube", True, (250,250,250)), (x0, y))
        y += ln+8
        ctitle = self.smallfont.render("Keyboard Controls:", True, (220,222,240))
        self.screen.blit(ctitle, (x0,y)); y += ln-5
        for line in [
            "ESC : Quit      [U] : Undo",
            "[SPACE] : Scramble",
            "[R] : Reset     [S] : Solve",
            "[F/L/R/B/U/D] : Rotate (CW)",
            "Shift+[face] : CCW rotation",
        ]:
            t = self.tinyfont.render(line, True, (190,200,210))
            self.screen.blit(t, (x0, y)); y += ln-13
        y += 12
        histlbl = self.smallfont.render("Move history:", True, (170,180,200))
        self.screen.blit(histlbl, (x0, y)); y += ln-12
        # Move history wrapping in side panel width
        mhist = self.cube.move_history[-18:]
        mhist_str = " ".join(mhist)
        words = mhist_str.split()
        mline = ""
        yoff = 0
        while words:
            while words and len(mline + " " + words[0]) < 29:
                mline = mline + " " + words.pop(0)
            mt = self.tinyfont.render(mline.strip(), True, (250,120,120))
            self.screen.blit(mt, (x0, y+2+yoff))
            yoff += 18
            mline = ""
    def process_window_resize(self):
        self.width, self.height = self.screen.get_size()
        self.setup_buttons()
    def start_solve_anim(self):
        if not self.cube.move_history: return
        self.solve_animating = True
        self.solve_anim_moves = self.cube.solve_anim_moves()
        self.last_anim_time = time.time()
    def do_solve_anim_step(self):
        now = time.time()
        if self.solve_animating and self.solve_anim_moves:
            if now - self.last_anim_time >= 1.0/SOLVE_SPEED:
                move = self.solve_anim_moves.pop(0)
                self.cube.rotate_face(move[0], clockwise=move[1], record=False)
                if self.cube.move_history: self.cube.move_history.pop(-1)
                self.last_anim_time = now
        if not self.solve_anim_moves:
            self.solve_animating = False
    def run(self):
        running = True
        clock = pygame.time.Clock()
        while running:
            mx, my = pygame.mouse.get_pos()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.VIDEORESIZE:
                    self.screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)
                    self.process_window_resize()
                elif not self.solve_animating and event.type == pygame.KEYDOWN:
                    k, mod = event.key, pygame.key.get_mods()
                    shift = mod & pygame.KMOD_SHIFT
                    face_keys = {pygame.K_f:"F", pygame.K_b:"B", pygame.K_u:"U",
                                pygame.K_d:"D", pygame.K_r:"R", pygame.K_l:"L"}
                    if k == pygame.K_ESCAPE: running = False
                    elif k == pygame.K_SPACE: self.cube.scramble()
                    elif k == pygame.K_r: self.cube.reset_cube()
                    elif k == pygame.K_s: self.start_solve_anim()
                    elif k == pygame.K_u: self.cube.undo()
                    elif k in face_keys:
                        self.cube.rotate_face(face_keys[k], clockwise=not shift)
                elif not self.solve_animating and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.buttons[0].is_clicked(event): self.cube.scramble()
                    elif self.buttons[1].is_clicked(event): self.cube.reset_cube()
                    elif self.buttons[2].is_clicked(event): self.start_solve_anim()
                    elif self.buttons[3].is_clicked(event): self.cube.undo()
            if self.solve_animating: self.do_solve_anim_step()
            self.screen.fill(self.BG)
            self.draw_cube()
            self.draw_panel_and_buttons()
            self.draw_side_panel()
            pygame.display.flip()
            clock.tick(60)
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    Cube2DApp().run()
