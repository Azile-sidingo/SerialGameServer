"""UART transport only. The STM32 firmware owns the board, rules and AI.

The Python client never evaluates a move or picks a square for the AI.
"""
from __future__ import annotations

from dataclasses import dataclass


class GameError(Exception):
    """Communication or firmware command error, suitable for showing in the GUI."""


@dataclass(frozen=True)
class GameSnapshot:
    board: str = '.........'
    active: bool = False
    winner: str | None = None
    draw: bool = False

    @property
    def turn(self) -> str:
        """Display-only turn derived from X-always-first board representation."""
        return 'X' if self.board.count('X') == self.board.count('O') else 'O'

    @property
    def finished(self) -> bool:
        return self.winner is not None or self.draw


def parse_response(response: str) -> GameSnapshot:
    """Read the board and outcome reported by C (do not recompute rules)."""
    if response == 'OK: IDLE':
        return GameSnapshot()
    parts = response.split()
    if not parts or parts[0] != 'OK:':
        raise GameError(f'Unexpected STM32 response: {response!r}')
    boards = [part[6:] for part in parts if part.startswith('BOARD:')]
    if len(boards) != 1:
        raise GameError(f'Missing board in STM32 response: {response!r}')
    board = boards[0]
    if len(board) != 9 or any(ch not in '.XO' for ch in board):
        raise GameError(f'Invalid STM32 board: {board!r}')
    winners = [part[4:] for part in parts if part.startswith('WIN:')]
    if len(winners) > 1 or (winners and winners[0] not in ('X', 'O')):
        raise GameError(f'Invalid STM32 result: {response!r}')
    winner = winners[0] if winners else None
    draw = 'DRAW' in parts
    if winner and draw:
        raise GameError(f'Contradictory STM32 result: {response!r}')
    game_over = 'GAME_OVER' in parts
    if game_over and not (winner or draw):
        raise GameError(f'Incomplete STM32 game-over response: {response!r}')
    return GameSnapshot(board, not (winner or draw or game_over), winner, draw)


class SerialClient:
    """Thin C-protocol client. All gameplay commands go to the STM32."""

    def __init__(self, port: str, baudrate: int = 38400,
                 timeout: float = 8.0, serial_factory=None):
        if not port:
            raise GameError('Enter the serial port (for example COM3).')
        if serial_factory is None:
            try:
                import serial
            except ImportError as exc:
                raise GameError('Install PySerial: py -3 -m pip install pyserial') from exc
            serial_factory = serial.Serial
        try:
            self.conn = serial_factory(port=port, baudrate=baudrate,
                                       timeout=timeout, write_timeout=timeout)
        except Exception as exc:
            raise GameError(f'Cannot connect to {port}: {exc}') from exc
        self.snapshot = GameSnapshot()
        try:
            response = self._command('STATE')
            self.snapshot = parse_response(response)
            if response == 'OK: IDLE' and self._command('CONNECT') != 'OK':
                raise GameError('STM32 did not accept CONNECT.')
        except Exception:
            self.conn.close()
            raise

    def _command(self, command: str) -> str:
        try:
            self.conn.write((command + '\n').encode('ascii'))
            result = self.conn.readline().decode('ascii', errors='replace').strip()
        except Exception as exc:
            raise GameError(f'STM32 communication failed: {exc}') from exc
        if not result:
            raise GameError('No response from the STM32. Check connection and baud rate.')
        if result.startswith('NACK:'):
            raise GameError(f'STM32 rejected {command}: {result}')
        return result

    def set_mode(self, mode: str, difficulty: str = 'medium',
                 human_mark: str = 'X') -> None:
        """Tell the firmware how to play the NEXT round."""
        if mode == 'pvp':
            command = 'MODE:PVP'
        elif mode == 'ai' and difficulty in ('easy', 'medium', 'hard') and human_mark in ('X', 'O'):
            ai_mark = 'O' if human_mark == 'X' else 'X'
            command = f'MODE:AI:{difficulty.upper()}:{ai_mark}'
        else:
            raise GameError('Unsupported mode, difficulty, or playing mark.')
        if self._command(command) != 'OK':
            raise GameError('STM32 did not accept the selected game mode.')

    def new_game(self) -> GameSnapshot:
        self.snapshot = parse_response(self._command('NEW'))
        return self.snapshot

    def move(self, index: int) -> GameSnapshot:
        if not 0 <= index <= 8:
            raise GameError('Square must be between 0 and 8.')
        # In AI mode, firmware performs the AI reply BEFORE responding.
        self.snapshot = parse_response(self._command(f'MOVE:{index}'))
        return self.snapshot

    def resign(self) -> GameSnapshot:
        self.snapshot = parse_response(self._command('RESIGN'))
        return self.snapshot

    def close(self) -> None:
        if not self.conn.is_open:
            return
        try:
            # Preserve firmware's original requirement: DISCONNECT only after a game.
            if self.snapshot.active:
                self.resign()
            if self.snapshot.finished:
                self._command('DISCONNECT')
        except GameError:
            pass
        finally:
            self.conn.close()
