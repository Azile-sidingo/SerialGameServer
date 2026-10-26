#ifndef GAME_H
#define GAME_H

/* Existing 3x3 rules: X starts, '.' denotes an empty square. */
typedef enum {
    MOVE_OK,
    MOVE_OUT_OF_RANGE,
    MOVE_OCCUPIED
} MoveResult;

typedef enum {
    STATUS_ONGOING,
    STATUS_WIN_X,
    STATUS_WIN_O,
    STATUS_DRAW
} GameStatus;

typedef enum {
    AI_EASY,
    AI_MEDIUM,
    AI_HARD
} AIDifficulty;

extern char game_board[10]; /* Nine cells + terminating NUL. */
extern char current_player;

void Game_Init(void);
MoveResult Game_ApplyMove(int index);
GameStatus Game_CheckStatus(void);

/* Returns a valid empty index, or -1 if it is not the AI's turn. */
int Game_SelectAIMove(char ai_mark, AIDifficulty difficulty);

#endif
