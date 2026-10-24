/* game.h */
#ifndef GAME_H
#define GAME_H

/* Define strict outcomes for any move attempt */
typedef enum {
    MOVE_OK,
    MOVE_OUT_OF_RANGE,
    MOVE_OCCUPIED
} MoveResult;

/* Define the possible states of the game board */
typedef enum {
    STATUS_ONGOING,
    STATUS_WIN_X,
    STATUS_WIN_O,
    STATUS_DRAW
} GameStatus;

extern char game_board[10];
extern char current_player;

void Game_Init(void);
MoveResult Game_ApplyMove(int index);
GameStatus Game_CheckStatus(void);

#endif /* GAME_H */
