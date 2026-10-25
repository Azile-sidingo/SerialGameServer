import tkinter as tk
from tkinter import messagebox
import serial

class TicTacToeGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Tic-Tac-Toe Serial Client")
        self.root.geometry("400x450") # Widened to fit the third button
       
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
       
        self.serial_conn = None
       
        # --- Controls Frame ---
        self.top_frame = tk.Frame(root)
        self.top_frame.pack(pady=10)
       
        self.connect_btn = tk.Button(self.top_frame, text="Connect", command=self.connect_to_board, width=10)
        self.connect_btn.grid(row=0, column=0, padx=5)
       
        self.start_btn = tk.Button(self.top_frame, text="Start Game", command=self.start_game, width=10, state=tk.DISABLED)
        self.start_btn.grid(row=0, column=1, padx=5)

        self.resign_btn = tk.Button(self.top_frame, text="Resign", command=self.resign_game, width=10, state=tk.DISABLED)
        self.resign_btn.grid(row=0, column=2, padx=5)
       
        self.status_label = tk.Label(root, text="Status: Disconnected", fg="red")
        self.status_label.pack(pady=5)
       
        # --- Grid Frame ---
        self.grid_frame = tk.Frame(root)
        self.grid_frame.pack(pady=10)
       
        self.buttons = []
        for i in range(9):
            btn = tk.Button(self.grid_frame, text="", font=('Arial', 24, 'bold'), width=5, height=2, state=tk.DISABLED,
                            command=lambda idx=i: self.send_move(idx))
            row = i // 3
            col = i % 3
            btn.grid(row=row, column=col, padx=2, pady=2)
            self.buttons.append(btn)

    def send_command(self, cmd):
        if not self.serial_conn or not self.serial_conn.is_open:
            return None
        try:
            self.serial_conn.write(f"{cmd}\n".encode('ascii'))
            response = self.serial_conn.readline().decode('ascii').strip()
            return response
        except Exception as e:
            messagebox.showerror("Serial Error", str(e))
            return None

    def connect_to_board(self):
        try:
            self.serial_conn = serial.Serial('COM3', 38400, timeout=2)
            response = self.send_command("CONNECT")
           
            if response == "OK":
                self.status_label.config(text="Status: Connected (IDLE)", fg="blue")
                self.connect_btn.config(state=tk.DISABLED)
                self.start_btn.config(state=tk.NORMAL)
            else:
                messagebox.showerror("Error", f"Unexpected response: {response}")
                self.serial_conn.close()
               
        except serial.SerialException as e:
            messagebox.showerror("Port Error", f"Could not open COM3.\n\nDetails: {e}")

    def start_game(self):
        response = self.send_command("NEW")
        if response and response.startswith("OK: BOARD:"):
            self.status_label.config(text="Status: IN PROGRESS", fg="green")
            self.parse_and_update_board(response)
            self.enable_grid()
            self.resign_btn.config(state=tk.NORMAL) # Enable Resign when game starts
        else:
            messagebox.showerror("Error", f"Failed to start game. Response: {response}")

    def send_move(self, index):
        response = self.send_command(f"MOVE:{index}")
        if not response:
            return
           
        if response.startswith("OK: BOARD:"):
            self.parse_and_update_board(response)
        elif response.startswith("NACK:"):
            messagebox.showwarning("Invalid Move", response)

    def resign_game(self):
        """Sends the RESIGN command and parses the STM32's WIN response."""
        response = self.send_command("RESIGN")
        if response and response.startswith("OK: BOARD:"):
            self.parse_and_update_board(response)
        elif response and response.startswith("NACK:"):
            messagebox.showwarning("Invalid Command", response)

    def parse_and_update_board(self, response):
        parts = response.split(" ")
       
        for part in parts:
            if part.startswith("BOARD:"):
                board_str = part.split(":")[1]
                for i in range(9):
                    char = board_str[i]
                    self.buttons[i].config(text="" if char == '.' else char)
       
        for part in parts:
            if part.startswith("WIN:"):
                winner = part.split(":")[1]
                self.status_label.config(text=f"Status: GAME OVER (Player {winner} Wins!)", fg="purple")
                self.disable_grid()
                messagebox.showinfo("Game Over", f"Player {winner} wins!")
            elif part == "DRAW":
                self.status_label.config(text="Status: GAME OVER (Draw)", fg="purple")
                self.disable_grid()
                messagebox.showinfo("Game Over", "The game is a draw!")

    def enable_grid(self):
        for btn in self.buttons:
            btn.config(state=tk.NORMAL)

    def disable_grid(self):
        for btn in self.buttons:
            btn.config(state=tk.DISABLED)
        self.resign_btn.config(state=tk.DISABLED) # Disable Resign when game ends

    def on_closing(self):
        if self.serial_conn and self.serial_conn.is_open:
            try:
                state_response = self.send_command("STATE")
                if state_response:
                    if "IN_PROGRESS" in state_response:
                        self.send_command("RESIGN")
                        self.send_command("DISCONNECT")
                    elif "GAME_OVER" in state_response:
                        self.send_command("DISCONNECT")
            except Exception:
                pass
            finally:
                self.serial_conn.close()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = TicTacToeGUI(root)
    root.mainloop()