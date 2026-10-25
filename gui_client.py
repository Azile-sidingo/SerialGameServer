"""Tic-Tac-Toe Arena: dark-themed GUI for the existing STM32 C firmware.

The board state, game rules, and all AI moves are owned by the MCU.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

from serial_client import GameError, SerialClient
from game_session import GameSession

# Visual-only win line highlighting; the STM32 provides the actual result.
WIN_LINES = ((0, 1, 2), (3, 4, 5), (6, 7, 8),
             (0, 3, 6), (1, 4, 7), (2, 5, 8),
             (0, 4, 8), (2, 4, 6))

# Consistent palette; X and O retain their colors everywhere in the UI.
BG = '#081321'
PANEL = '#112238'
PANEL_ALT = '#172C44'
TILE = '#203650'
TILE_HOVER = '#2A4661'
BORDER = '#30445B'
WHITE = '#F5F8FE'
MUTED = '#99ADC2'
TEAL = '#60E7D3'
CORAL = '#FFAD84'
GOLD = '#FFD07B'
BUTTON_DARK = '#254058'
FONT = 'Segoe UI'


def rounded_rect(canvas: tk.Canvas, x1: float, y1: float, x2: float,
                 y2: float, radius: int, **options):
    """Draw a rounded rectangle without optional imaging libraries."""
    r = min(radius, int((x2 - x1) / 2), int((y2 - y1) / 2))
    coords = [x1+r, y1, x2-r, y1, x2, y1, x2, y1+r,
              x2, y2-r, x2, y2, x2-r, y2, x1+r, y2,
              x1, y2, x1, y2-r, x1, y1+r, x1, y1]
    return canvas.create_polygon(coords, smooth=True, splinesteps=16, **options)


def label(parent, text: str, size: int = 12, color: str = WHITE,
          weight: str = 'normal', **kwargs) -> tk.Label:
    return tk.Label(parent, text=text, bg=parent.cget('bg'), fg=color,
                    font=(FONT, size, weight), **kwargs)


def action_button(parent, text: str, command, primary: bool = False,
                  bg: str | None = None, fg: str | None = None, height: int = 2):
    normal = bg or (TEAL if primary else BUTTON_DARK)
    hover = '#8FF2E3' if primary else TILE_HOVER
    btn = tk.Button(parent, text=text, command=command,
                    bg=normal, fg=fg or (BG if primary else WHITE),
                    activebackground=hover, activeforeground=BG if primary else WHITE,
                    relief='flat', borderwidth=0, cursor='hand2',
                    font=(FONT, 11, 'bold'), height=height, padx=17)
    btn.bind('<Enter>', lambda _: btn.config(bg=hover))
    btn.bind('<Leave>', lambda _: btn.config(bg=normal))
    return btn


class TicTacToeGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title('TIC TAC TOE  •  ARENA')
        self.root.geometry('1010x740')
        self.root.minsize(900, 720)
        self.root.configure(bg=BG)
        self.root.protocol('WM_DELETE_WINDOW', self.on_closing)

        self.mode = 'ai'
        self.difficulty = 'medium'
        self.human_mark = 'X'
        self.port = tk.StringVar(value='COM3')
        self.session: GameSession | None = None
        self.hover_square: int | None = None
        self.board_canvas: tk.Canvas | None = None

        self.main = tk.Frame(root, bg=BG)
        self.main.pack(fill='both', expand=True)
        self.root.bind('<Key>', self._keyboard_move)
        self.show_menu()

    def _clear(self):
        for child in self.main.winfo_children():
            child.destroy()
        self.board_canvas = None

    def _header(self, parent: tk.Widget, subtitle: str):
        top = tk.Frame(parent, bg=BG)
        top.pack(fill='x', pady=(13, 13))
        emblem = tk.Frame(top, bg=PANEL, padx=12, pady=9)
        emblem.pack(side='left', padx=(0, 12))
        label(emblem, '✕  ◯', 17, TEAL, 'bold').pack()
        title_block = tk.Frame(top, bg=BG)
        title_block.pack(side='left')
        label(title_block, 'TIC TAC TOE', 23, WHITE, 'bold').pack(anchor='w')
        label(title_block, subtitle, 10, MUTED).pack(anchor='w', pady=(1, 0))
        label(top, 'ARENA  /  01', 10, MUTED, 'bold').pack(side='right', pady=8)

    def show_menu(self):
        self._clear()
        content = tk.Frame(self.main, bg=BG, padx=40, pady=17)
        content.pack(fill='both', expand=True)
        self._header(content, 'A classic rivalry, reimagined.')

        heading = tk.Frame(content, bg=BG)
        heading.pack(fill='x', pady=(16, 14))
        label(heading, 'Choose your arena', 29, WHITE, 'bold').pack(anchor='w')
        label(heading, 'Pick a mode and challenge level. Your STM32 handles the game.',
              11, MUTED).pack(anchor='w', pady=(4, 0))

        cards = tk.Frame(content, bg=BG)
        cards.pack(fill='x', pady=(0, 20))
        cards.grid_columnconfigure(0, weight=1, uniform='m')
        cards.grid_columnconfigure(1, weight=1, uniform='m')
        self.mode_cards = {}
        for column, (mode, graphic, title, description) in enumerate((
            ('pvp', '✕  vs  ◯', 'Two players', 'Two people · one PC · STM32 rules'),
            ('ai', '✕  vs  ✦', 'Play the AI', 'Easy, Medium, or Hard · C-powered AI'),
        )):
            card = tk.Frame(cards, bg=PANEL, padx=20, pady=16,
                            highlightthickness=2, highlightbackground=BORDER,
                            cursor='hand2')
            card.grid(row=0, column=column, sticky='nsew', padx=(0, 9) if column == 0 else (9, 0))
            graphic_label = label(card, graphic, 23, TEAL if mode == 'pvp' else CORAL, 'bold')
            graphic_label.pack(anchor='w', pady=(1, 7))
            name = label(card, title, 16, WHITE, 'bold')
            name.pack(anchor='w')
            desc = label(card, description, 10, MUTED)
            desc.pack(anchor='w', pady=(4, 0))
            for widget in (card, graphic_label, name, desc):
                widget.bind('<Button-1>', lambda _, choice=mode: self._select_mode(choice))
                widget.config(cursor='hand2')
            self.mode_cards[mode] = card

        self.settings = tk.Frame(content, bg=PANEL, padx=22, pady=18)
        self.settings.pack(fill='x')
        label(self.settings, 'GAME SETTINGS', 10, MUTED, 'bold').pack(anchor='w', pady=(0, 13))
        self.settings_body = tk.Frame(self.settings, bg=PANEL)
        self.settings_body.pack(fill='x')

        bottom = tk.Frame(content, bg=BG)
        bottom.pack(fill='x', pady=(20, 0))
        label(bottom, 'STM32 C GAME ENGINE  •  SERIAL LINK REQUIRED', 9, MUTED, 'bold').pack(side='left')
        action_button(bottom, 'START GAME    →', self.start_game, primary=True).pack(side='right')

        self._select_mode(self.mode)

    def _segmented(self, parent, values: tuple[str, ...], selected: str,
                   on_select, display=None):
        row = tk.Frame(parent, bg=PANEL)
        for v in values:
            on = v == selected
            bg = TEAL if on else BUTTON_DARK
            fg = BG if on else MUTED
            button = tk.Button(row, text=display(v) if display else v.title(),
                               command=lambda value=v: on_select(value),
                               font=(FONT, 10, 'bold'), bg=bg, fg=fg,
                               relief='flat', borderwidth=0, cursor='hand2',
                               activebackground=TEAL, activeforeground=BG,
                               padx=18, pady=9)
            button.pack(side='left', padx=(0, 7))
        return row

    def _select_mode(self, mode):
        self.mode = mode
        for name, card in self.mode_cards.items():
            card.config(highlightbackground=TEAL if name == mode else BORDER)
        self._render_settings()

    def _set_difficulty(self, value):
        self.difficulty = value
        self._render_settings()

    def _set_mark(self, value):
        self.human_mark = value
        self._render_settings()

    def _render_settings(self):
        for child in self.settings_body.winfo_children():
            child.destroy()
        choices = tk.Frame(self.settings_body, bg=PANEL)
        choices.pack(fill='x')
        if self.mode == 'ai':
            col1 = tk.Frame(choices, bg=PANEL)
            col1.pack(side='left', fill='x', expand=True)
            label(col1, 'DIFFICULTY', 10, MUTED, 'bold').pack(anchor='w', pady=(0, 6))
            self._segmented(col1, ('easy', 'medium', 'hard'), self.difficulty,
                            self._set_difficulty).pack(anchor='w')
            col2 = tk.Frame(choices, bg=PANEL)
            col2.pack(side='left', fill='x', expand=True)
            label(col2, 'YOUR MARK', 10, MUTED, 'bold').pack(anchor='w', pady=(0, 6))
            self._segmented(col2, ('X', 'O'), self.human_mark,
                            self._set_mark, display=lambda v: f'PLAY {v}').pack(anchor='w')
        else:
            label(choices, 'LOCAL MULTIPLAYER', 11, WHITE, 'bold').pack(anchor='w')
            label(choices, 'Player 1 is ✕ and goes first. Player 2 is ◯.', 10, MUTED).pack(anchor='w', pady=(5, 0))

        separator = tk.Frame(self.settings_body, bg=BORDER, height=1)
        separator.pack(fill='x', pady=15)
        connection = tk.Frame(self.settings_body, bg=PANEL)
        connection.pack(fill='x')
        left = tk.Frame(connection, bg=PANEL)
        left.pack(side='left', fill='x', expand=True)
        label(left, 'GAME ENGINE', 10, MUTED, 'bold').pack(anchor='w', pady=(0, 7))
        label(left, 'STM32  /  C GAME LOGIC', 11, TEAL, 'bold').pack(anchor='w')
        label(left, 'All turns and AI decisions run on your board.', 10, MUTED).pack(anchor='w', pady=(5, 0))
        right = tk.Frame(connection, bg=PANEL)
        right.pack(side='left', fill='x', expand=True)
        label(right, 'SERIAL PORT   /   38400 BAUD', 10, MUTED, 'bold').pack(anchor='w', pady=(0, 7))
        tk.Entry(right, textvariable=self.port, font=(FONT, 12), bg=BUTTON_DARK,
                 fg=WHITE, insertbackground=WHITE, relief='flat', width=16).pack(anchor='w', ipady=8)

    def start_game(self):
        try:
            client = SerialClient(self.port.get().strip())
            session = GameSession(client, self.mode, self.difficulty, self.human_mark)
            try:
                # MODE is sent before NEW; AI moves happen in C automatically.
                session.new_round()
            except Exception:
                session.close()
                raise
        except (GameError, ValueError) as exc:
            messagebox.showerror('Cannot start game', str(exc), parent=self.root)
            return
        self.session = session
        self.show_game()

    def show_game(self):
        self._clear()
        session = self.session
        content = tk.Frame(self.main, bg=BG, padx=30, pady=12)
        content.pack(fill='both', expand=True)
        self._header(content, 'Every square changes the story.')
        top = tk.Frame(content, bg=BG)
        top.pack(fill='x', pady=(3, 14))
        label(top, f'ROUND {session.round:02d}', 10, TEAL, 'bold').pack(side='left')
        label(top, 'STM32 CONNECTED  •  C GAME ENGINE',
              10, MUTED, 'bold').pack(side='right')

        body = tk.Frame(content, bg=BG)
        body.pack(fill='both', expand=True)
        board_panel = tk.Frame(body, bg=PANEL, padx=16, pady=13)
        board_panel.pack(side='left', anchor='n', padx=(0, 18))
        title_row = tk.Frame(board_panel, bg=PANEL)
        title_row.pack(fill='x', pady=(0, 5))
        label(title_row, 'THE BOARD', 12, WHITE, 'bold').pack(side='left')
        label(title_row, '3 × 3 GRID', 10, MUTED).pack(side='right')

        self.board_canvas = tk.Canvas(board_panel, width=450, height=450, bg=PANEL,
                                      highlightthickness=0, cursor='hand2')
        self.board_canvas.pack()
        self.board_canvas.bind('<Button-1>', self._canvas_click)
        self.board_canvas.bind('<Motion>', self._canvas_hover)
        self.board_canvas.bind('<Leave>', lambda _: self._reset_hover())
        label(board_panel, 'TIP   Click a square · or press keys 1–9', 10, MUTED).pack(pady=(6, 0))

        side = tk.Frame(body, bg=BG)
        side.pack(side='left', fill='both', expand=True, anchor='n')

        summary = tk.Frame(side, bg=PANEL, padx=20, pady=20)
        summary.pack(fill='x', pady=(0, 13))
        label(summary, 'MATCH STATUS', 10, MUTED, 'bold').pack(anchor='w')
        self.status_big = label(summary, '', 19, WHITE, 'bold', wraplength=260, justify='left')
        self.status_big.pack(anchor='w', pady=(10, 6))
        self.status_hint = label(summary, '', 10, MUTED, wraplength=250, justify='left')
        self.status_hint.pack(anchor='w')
        self.turn_chip = label(summary, '', 10, TEAL, 'bold')
        self.turn_chip.pack(anchor='w', pady=(13, 0))

        scores = tk.Frame(side, bg=PANEL, padx=20, pady=15)
        scores.pack(fill='x', pady=(0, 13))
        label(scores, 'SCOREBOARD', 10, MUTED, 'bold').pack(anchor='w', pady=(0, 9))
        self.score_x = label(scores, '', 12, WHITE, 'bold')
        self.score_x.pack(anchor='w', pady=4)
        self.score_o = label(scores, '', 12, WHITE, 'bold')
        self.score_o.pack(anchor='w', pady=4)
        self.score_d = label(scores, '', 11, MUTED)
        self.score_d.pack(anchor='w', pady=(6, 0))

        controls = tk.Frame(side, bg=BG)
        controls.pack(fill='x')
        self.new_btn = action_button(controls, '↻   NEW ROUND', self.new_round, primary=True)
        self.new_btn.pack(fill='x', pady=(0, 8))
        self.resign_btn = action_button(controls, '✕   RESIGN ROUND', self.resign_game)
        self.resign_btn.pack(fill='x', pady=(0, 8))
        action_button(controls, '←   CHANGE MODE', self.back_to_menu,
                      bg=PANEL_ALT).pack(fill='x')
        self._refresh()

    def _square_at(self, x, y) -> int | None:
        start, size, gap = 15, 130, 15
        for i in range(9):
            x0 = start + (i % 3) * (size + gap)
            y0 = start + (i // 3) * (size + gap)
            if x0 <= x < x0 + size and y0 <= y < y0 + size:
                return i
        return None

    def _canvas_hover(self, event):
        hovered = (self._square_at(event.x, event.y) if self.session.can_play else None)
        if hovered is not None and self.session.snapshot.board[hovered] != '.':
            hovered = None
        if hovered != self.hover_square:
            self.hover_square = hovered
            self._draw_board()

    def _reset_hover(self):
        if self.hover_square is not None:
            self.hover_square = None
            self._draw_board()

    def _draw_board(self):
        canvas = self.board_canvas
        if canvas is None:
            return
        canvas.delete('all')
        board = self.session.snapshot.board
        start, size, gap = 15, 130, 15
        for i, mark in enumerate(board):
            x = start + (i % 3) * (size + gap)
            y = start + (i // 3) * (size + gap)
            chosen = self.hover_square == i and self.session.can_play
            rounded_rect(canvas, x, y, x + size, y + size, 18,
                         fill=TILE_HOVER if chosen else TILE, outline='')
            cx, cy = x + size / 2, y + size / 2
            pad = 36
            if mark == 'X':
                canvas.create_line(x+pad, y+pad, x+size-pad, y+size-pad,
                                   fill=TEAL, width=11, capstyle=tk.ROUND)
                canvas.create_line(x+size-pad, y+pad, x+pad, y+size-pad,
                                   fill=TEAL, width=11, capstyle=tk.ROUND)
            elif mark == 'O':
                canvas.create_oval(x+pad-2, y+pad-2, x+size-pad+2, y+size-pad+2,
                                   outline=CORAL, width=11)
            elif chosen:
                canvas.create_text(cx, cy, text=self.session.snapshot.turn,
                                   font=(FONT, 34, 'bold'), fill=MUTED)

        # Only a real 3-in-a-row produces a line; resignation does not.
        natural_winner = next(
            (board[a] for a, b, c in WIN_LINES
             if board[a] != '.' and board[a] == board[b] == board[c]), None
        ) if self.session.snapshot.winner else None
        if natural_winner:
            for a, b, c in WIN_LINES:
                if board[a] == board[b] == board[c] == natural_winner:
                    ax = start + (a % 3) * (size + gap) + size/2
                    ay = start + (a // 3) * (size + gap) + size/2
                    cx = start + (c % 3) * (size + gap) + size/2
                    cy = start + (c // 3) * (size + gap) + size/2
                    canvas.create_line(ax, ay, cx, cy, fill=GOLD, width=5,
                                       capstyle=tk.ROUND)
                    break

    def _refresh(self):
        session = self.session
        snap = session.snapshot
        self._draw_board()
        self.score_x.config(text=f'✕   {session.player_name("X")}       {session.scores["X"]}', fg=TEAL)
        self.score_o.config(text=f'◯   {session.player_name("O")}       {session.scores["O"]}', fg=CORAL)
        self.score_d.config(text=f'Drawn rounds       {session.scores["D"]}')
        if snap.winner:
            title = ('You win!' if session.mode == 'ai' and snap.winner == session.human_mark
                     else 'AI wins!' if session.mode == 'ai'
                     else f'{session.player_name(snap.winner)} wins!')
            hint = 'A brilliant finish. Fancy a rematch?'
            chip = 'ROUND COMPLETE'
        elif snap.draw:
            title, hint, chip = 'A perfect draw.', 'Well played by both sides.', 'ROUND COMPLETE'
        else:
            title = f'{session.player_name(snap.turn)} to play'
            hint = ('The STM32 replies as the AI after each move.'
                    if session.mode == 'ai' else 'Choose any open square on the board.')
            chip = f'{snap.turn}  TO MOVE'
        self.status_big.config(text=title)
        self.status_hint.config(text=hint)
        self.turn_chip.config(text=chip, fg=CORAL if snap.turn == 'O' else TEAL)
        self.resign_btn.config(state='normal' if session.can_play else 'disabled')

    def _canvas_click(self, event):
        index = self._square_at(event.x, event.y)
        if index is not None:
            self._make_move(index)

    def _keyboard_move(self, event):
        if not self.session or self.board_canvas is None:
            return
        if event.char in '123456789' and event.char:
            self._make_move(int(event.char) - 1)

    def _make_move(self, index):
        if not self.session or not self.session.can_play:
            return
        if self.session.snapshot.board[index] != '.':
            return
        try:
            self.session.play(index)
        except GameError as exc:
            self._error(exc)
            return
        self.hover_square = None
        self._refresh()

    def new_round(self):
        try:
            self.session.new_round()
        except GameError as exc:
            self._error(exc)
            return
        # Refresh heading and result without resetting session scores.
        self.show_game()

    def resign_game(self):
        if not self.session or not self.session.can_play:
            return
        try:
            self.session.resign()
        except GameError as exc:
            self._error(exc)
            return
        self._refresh()

    def back_to_menu(self):
        if self.session:
            self.session.close()
            self.session = None
        self.show_menu()

    def _error(self, error):
        messagebox.showerror('Game error', str(error), parent=self.root)

    def on_closing(self):
        if self.session:
            self.session.close()
            self.session = None
        self.root.destroy()


def main():
    root = tk.Tk()
    TicTacToeGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
