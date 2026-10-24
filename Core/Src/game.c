/* game.c */
#include "game.h"
#include <string.h>

char game_board[10];
char current_player;

void Game_Init(void)
{
    memset(game_board, '.', 9);
    game_board[9] = '\0';
    current_player = 'X';
}

MoveResult Game_ApplyMove(int index)
{
    if (index < 0 || index > 8)
    {
        return MOVE_OUT_OF_RANGE;
    }

    if (game_board[index] != '.')
    {
        return MOVE_OCCUPIED;
    }

    game_board[index] = current_player;

    if (current_player == 'X')
    {
        current_player = 'O';
    }
    else
    {
        current_player = 'X';
    }

    return MOVE_OK;
}

GameStatus Game_CheckStatus(void)
{
    /* The 8 possible winning combinations (rows, columns, diagonals) */
    int wins[8][3] = {
        {0, 1, 2}, {3, 4, 5}, {6, 7, 8},
        {0, 3, 6}, {1, 4, 7}, {2, 5, 8},
        {0, 4, 8}, {2, 4, 6}
    };

    /* 1. Check for a winner */
    for (int i = 0; i < 8; i++)
    {
        char a = game_board[wins[i][0]];
        char b = game_board[wins[i][1]];
        char c = game_board[wins[i][2]];

        if (a != '.' && a == b && b == c)
        {
            if (a == 'X') return STATUS_WIN_X;
            if (a == 'O') return STATUS_WIN_O;
        }
    }

    /* 2. Check for empty spaces (ongoing game) */
    for (int i = 0; i < 9; i++)
    {
        if (game_board[i] == '.')
        {
            return STATUS_ONGOING;
        }
    }

    /* 3. If no winner and no empty spaces, it is a draw */
    return STATUS_DRAW;
}
