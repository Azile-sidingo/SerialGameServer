"""Presentation/session state only. Board rules and AI live on the MCU."""
from __future__ import annotations

from serial_client import GameError, GameSnapshot, SerialClient


class GameSession:
    def __init__(self, client: SerialClient, mode: str,
                 difficulty: str = 'medium', human_mark: str = 'X'):
        if mode not in ('pvp', 'ai') or difficulty not in ('easy', 'medium', 'hard') or human_mark not in ('X', 'O'):
            raise ValueError('Unsupported mode, difficulty, or mark')
        self.client = client
        self.mode = mode
        self.difficulty = difficulty
        self.human_mark = human_mark
        self.snapshot = GameSnapshot()
        self.scores = {'X': 0, 'O': 0, 'D': 0}
        self.round = 0
        self._counted = False

    @property
    def can_play(self) -> bool:
        # The STM32 always returns an AI mode board with the human to move.
        return self.snapshot.active

    def player_name(self, mark: str) -> str:
        if self.mode == 'pvp':
            return f'Player {1 if mark == "X" else 2}'
        return 'You' if mark == self.human_mark else 'AI opponent'

    def new_round(self) -> GameSnapshot:
        self.client.set_mode(self.mode, self.difficulty, self.human_mark)
        self.snapshot = self.client.new_game()
        self.round += 1
        self._counted = False
        return self.snapshot

    def _record(self, snapshot: GameSnapshot) -> GameSnapshot:
        self.snapshot = snapshot
        if snapshot.finished and not self._counted:
            key = 'D' if snapshot.draw else snapshot.winner
            self.scores[key] += 1
            self._counted = True
        return snapshot

    def play(self, index: int) -> GameSnapshot:
        if not self.can_play:
            raise GameError('The round has ended. Start a new round.')
        if self.snapshot.board[index] != '.':
            raise GameError('That square is already occupied.')
        return self._record(self.client.move(index))

    def resign(self) -> GameSnapshot:
        if not self.can_play:
            raise GameError('No active round to resign from.')
        return self._record(self.client.resign())

    def close(self) -> None:
        self.client.close()
