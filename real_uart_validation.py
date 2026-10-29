"""Real-hardware validation for the EEE3095S UART Tic-Tac-Toe server.

Run with the GUI CLOSED so the COM port is available:
    py -3 -m pip install pyserial
    py -3 real_uart_validation.py --port COM3 --log real_uart_results.txt

CAUTION: This test intentionally resets and plays games on the connected STM32.
It is not a simulation. Every assertion checks the board's serial response.
"""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import re
import sys
import time

try:
    import serial
except ImportError:
    raise SystemExit("Missing pyserial. Install it with: py -3 -m pip install pyserial")


class BoardTester:
    def __init__(self, conn, pause: float, log_path: Path):
        self.conn = conn
        self.pause = pause
        self.events: list[str] = []
        self.passed = 0
        self.failed = 0
        self.log_path = log_path

    def note(self, message: str):
        print(message, flush=True)
        self.events.append(message)

    def command(self, request: str) -> str:
        self.conn.write((request + "\n").encode("ascii"))
        self.conn.flush()
        reply = self.conn.readline().decode("ascii", errors="replace").strip()
        self.note(f"TX {request!r}  ->  RX {reply!r}")
        if not reply:
            raise AssertionError(f"No reply received for {request!r}. Check COM port and baud rate.")
        # Driver updates LCD after sending UART reply; allow state transition to finish.
        time.sleep(self.pause)
        return reply

    def check(self, name: str, condition: bool, detail: str = ""):
        if condition:
            self.passed += 1
            self.note(f"PASS | {name}")
        else:
            self.failed += 1
            self.note(f"FAIL | {name}" + (f" | {detail}" if detail else ""))
            raise AssertionError(f"{name}: {detail}")

    def expect(self, request: str, expected: str, name: str):
        received = self.command(request)
        self.check(name, received == expected, f"expected {expected!r}, got {received!r}")
        return received

    def check_board(self, response: str, x: int, o: int, label: str, required: dict[int, str] | None = None):
        match = re.search(r"BOARD:([XO.]{9})", response)
        self.check(label + " (board format)", bool(match), f"response={response!r}")
        board = match.group(1)
        self.check(label + " (mark counts)", board.count("X") == x and board.count("O") == o,
                   f"board={board!r}, expected X={x}, O={o}")
        for i, mark in (required or {}).items():
            self.check(label + f" (cell {i})", board[i] == mark,
                       f"board={board!r}, expected cell {i}={mark}")
        return board

    def run(self):
        self.note("=== EEE3095S REAL STM32 UART VALIDATION ===")
        self.note(f"Timestamp: {datetime.now().astimezone().isoformat(timespec='seconds')}")
        self.note(f"Serial port: {self.conn.port} | baud: {self.conn.baudrate}")
        self.note("NOTE: These assertions send commands to the attached physical serial port.")

        # Reset the protocol to a known IDLE state regardless of its initial state.
        self.expect("MODE:PVP", "OK", "Configure two-player mode")
        self.expect("NEW", "OK: BOARD:.........", "Prepare clean board")
        self.command("RESIGN")
        self.expect("DISCONNECT", "OK", "Reach IDLE")
        self.expect("CONNECT", "OK", "CONNECT accepted while IDLE")
        self.expect("NEW", "OK: BOARD:.........", "NEW returns empty board")

        # Move validation: errors cannot change state.
        self.expect("MOVE:0", "OK: BOARD:X........", "Legal move updates board")
        original = self.expect("STATE", "OK: BOARD:X........ GAME IN_PROGRESS", "STATE after legal move")
        self.expect("MOVE:0", "NACK: OCCUPIED", "Occupied move rejected")
        self.expect("STATE", original, "Occupied move leaves board unchanged")
        self.expect("MOVE:9", "NACK: RANGE", "Out-of-range move rejected")
        self.expect("STATE", original, "Out-of-range move leaves board unchanged")
        self.expect("MOVE:abc", "NACK: BADCMD", "Malformed move rejected")
        self.expect("STATE", original, "Malformed move leaves board unchanged")
        self.expect("GARBAGE", "NACK: BADCMD", "Unknown command rejected")
        self.expect("STATE", original, "Unknown command leaves board unchanged")

        # A win for X, then out-of-state request.
        self.expect("NEW", "OK: BOARD:.........", "Reset for winning sequence")
        for idx in (0, 3, 1, 4):
            reply = self.command(f"MOVE:{idx}")
            self.check(f"Winning sequence legal move {idx}", reply.startswith("OK: BOARD:") and " WIN:" not in reply)
        self.expect("MOVE:2", "OK: BOARD:XXXOO.... WIN:X", "Detect X winning row")
        self.expect("STATE", "OK: BOARD:XXXOO.... GAME_OVER WIN:X", "GAME_OVER reflects X victory")
        self.expect("MOVE:8", "NACK: NOGAME", "Reject move after game over")
        self.expect("STATE", "OK: BOARD:XXXOO.... GAME_OVER WIN:X", "Game-over move unchanged")

        # Valid full-board draw sequence (no win before ninth move).
        self.expect("NEW", "OK: BOARD:.........", "Reset for draw sequence")
        draw_moves = (0, 1, 2, 4, 3, 5, 7, 6)
        for idx in draw_moves:
            reply = self.command(f"MOVE:{idx}")
            self.check(f"Draw sequence legal move {idx}", reply.startswith("OK: BOARD:") and " WIN:" not in reply and "DRAW" not in reply)
        self.expect("MOVE:8", "OK: BOARD:XOXXOOOXX DRAW", "Detect full-board draw")
        self.expect("STATE", "OK: BOARD:XOXXOOOXX GAME_OVER DRAW", "GAME_OVER reflects draw")

        # AI X moves first; AI O moves after first human X move.
        for level in ("EASY", "MEDIUM", "HARD"):
            self.expect(f"MODE:AI:{level}:X", "OK", f"Configure AI {level} as X")
            reply = self.command("NEW")
            board = self.check_board(reply, 1, 0, f"AI {level} first move")
            human_move = board.index(".")
            reply = self.command(f"MOVE:{human_move}")
            self.check_board(reply, 2, 1, f"AI {level} responds legally", {human_move: "O"})

            self.expect(f"MODE:AI:{level}:O", "OK", f"Configure AI {level} as O")
            self.expect("NEW", "OK: BOARD:.........", f"AI {level} O new board empty")
            reply = self.command("MOVE:0")
            self.check_board(reply, 1, 1, f"AI {level} O moves legally", {0: "X"})

        # Resign & clean disconnect while PvP is configured.
        self.expect("MODE:PVP", "OK", "Restore two-player mode")
        self.expect("NEW", "OK: BOARD:.........", "Start final PvP game")
        self.expect("RESIGN", "OK: BOARD:......... WIN:O", "Resignation ends match")
        self.expect("DISCONNECT", "OK", "Clean disconnect after game over")
        self.expect("STATE", "OK: IDLE", "IDLE confirmed after disconnect")

    def save(self):
        footer = f"\nSUMMARY: {self.passed} passed, {self.failed} failed\n"
        self.note(footer.strip())
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_path.write_text("\n".join(self.events) + "\n", encoding="utf-8")
        self.note(f"Saved evidence: {self.log_path.resolve()}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Test EEE3095S firmware through its real UART COM port.")
    parser.add_argument("--port", required=True, help="STM32 virtual COM port, e.g., COM3 on Windows")
    parser.add_argument("--baud", type=int, default=38400)
    parser.add_argument("--pause", type=float, default=0.3,
                        help="Delay in seconds after replies to allow LCD update")
    parser.add_argument("--log", type=Path, default=Path("real_uart_results.txt"))
    args = parser.parse_args()
    if args.pause < 0:
        parser.error("--pause must be >= 0")
    try:
        with serial.Serial(args.port, args.baud, timeout=2.5, write_timeout=2.5) as conn:
            time.sleep(0.5)
            conn.reset_input_buffer()
            tester = BoardTester(conn, args.pause, args.log)
            try:
                tester.run()
            except (AssertionError, OSError, serial.SerialException) as exc:
                tester.note("TEST STOPPED: " + str(exc))
                tester.failed += 1
            finally:
                tester.save()
            return 1 if tester.failed else 0
    except (OSError, serial.SerialException) as exc:
        print(f"Cannot open serial port {args.port!r}: {exc}", file=sys.stderr)
        print("Close the Tkinter GUI and any serial monitor before testing.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
