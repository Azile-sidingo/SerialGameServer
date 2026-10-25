/* game.c -- Existing tic-tac-toe rules + embedded AI move selection. */
#include "game.h"
#include <string.h>
#include <stdint.h>

char game_board[10];
char current_player;

/* The same eight winning combinations used by the original implementation. */
static const uint8_t WIN_LINES[8][3] = {
    {0, 1, 2}, {3, 4, 5}, {6, 7, 8},
    {0, 3, 6}, {1, 4, 7}, {2, 5, 8},
    {0, 4, 8}, {2, 4, 6}
};

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
    /* Original win/draw/ongoing logic is intentionally unchanged. */
    for (int i = 0; i < 8; i++)
    {
        char a = game_board[WIN_LINES[i][0]];
        char b = game_board[WIN_LINES[i][1]];
        char c = game_board[WIN_LINES[i][2]];
        if (a != '.' && a == b && b == c)
        {
            if (a == 'X') return STATUS_WIN_X;
            if (a == 'O') return STATUS_WIN_O;
        }
    }
    for (int i = 0; i < 9; i++)
    {
        if (game_board[i] == '.')
        {
            return STATUS_ONGOING;
        }
    }
    return STATUS_DRAW;
}

/* AI implementation below reads the board but never changes the live game.
 * The protocol applies the returned index via the original Game_ApplyMove(). */

/* Small pseudo-random generator: no HAL dependency or heap allocations. */
static uint32_t random_state = 0xAB93D481u;

static uint32_t next_random(void)
{
    random_state ^= random_state << 13;
    random_state ^= random_state >> 17;
    random_state ^= random_state << 5;
    return random_state;
}

static char board_winner(const char board[10])
{
    for (int i = 0; i < 8; ++i)
    {
        char a = board[WIN_LINES[i][0]];
        if (a != '.' && a == board[WIN_LINES[i][1]] &&
            a == board[WIN_LINES[i][2]])
        {
            return a;
        }
    }
    return '.';
}

static int random_empty_square(const char board[10])
{
    int choices[9];
    int count = 0;
    for (int i = 0; i < 9; ++i)
    {
        if (board[i] == '.') choices[count++] = i;
    }
    return count ? choices[next_random() % (uint32_t)count] : -1;
}

static int find_immediate_win(char board[10], char mark)
{
    for (int i = 0; i < 9; ++i)
    {
        if (board[i] != '.') continue;
        board[i] = mark;
        char found = board_winner(board);
        board[i] = '.';
        if (found == mark) return i;
    }
    return -1;
}

/* Medium: take a win, block an immediate loss, then favour strong positions. */
static int medium_move(char board[10], char ai_mark)
{
    char human_mark = (ai_mark == 'X') ? 'O' : 'X';
    int move = find_immediate_win(board, ai_mark);
    if (move >= 0) return move;
    move = find_immediate_win(board, human_mark);
    if (move >= 0) return move;
    if (board[4] == '.') return 4;

    static const uint8_t corners[4] = {0, 2, 6, 8};
    int free_corners[4];
    int count = 0;
    for (int i = 0; i < 4; ++i)
    {
        if (board[corners[i]] == '.') free_corners[count++] = corners[i];
    }
    if (count) return free_corners[next_random() % (uint32_t)count];
    return random_empty_square(board);
}

/* Hard: full-depth minimax with alpha-beta pruning. With only nine squares,
 * the maximum recursion depth is small and no heap is required. */
static int minimax(char board[10], char turn, char ai_mark,
                   int depth, int alpha, int beta)
{
    char win = board_winner(board);
    if (win == ai_mark) return 10 - depth;
    if (win != '.') return depth - 10;

    int empty_count = 0;
    for (int i = 0; i < 9; ++i)
    {
        if (board[i] == '.') ++empty_count;
    }
    if (!empty_count) return 0;

    const int maximizing = turn == ai_mark;
    int best = maximizing ? -100 : 100;
    static const uint8_t order[9] = {4, 0, 2, 6, 8, 1, 3, 5, 7};
    for (int j = 0; j < 9; ++j)
    {
        int i = order[j];
        if (board[i] != '.') continue;
        board[i] = turn;
        int score = minimax(board, turn == 'X' ? 'O' : 'X', ai_mark,
                            depth + 1, alpha, beta);
        board[i] = '.';
        if (maximizing)
        {
            if (score > best) best = score;
            if (best > alpha) alpha = best;
        }
        else
        {
            if (score < best) best = score;
            if (best < beta) beta = best;
        }
        if (beta <= alpha) break;
    }
    return best;
}

static int hard_move(char board[10], char ai_mark)
{
    static const uint8_t order[9] = {4, 0, 2, 6, 8, 1, 3, 5, 7};
    int best_move = -1;
    int best_score = -100;
    for (int j = 0; j < 9; ++j)
    {
        int i = order[j];
        if (board[i] != '.') continue;
        board[i] = ai_mark;
        int score = minimax(board, ai_mark == 'X' ? 'O' : 'X',
                            ai_mark, 1, -100, 100);
        board[i] = '.';
        if (score > best_score)
        {
            best_score = score;
            best_move = i;
        }
    }
    return best_move;
}

int Game_SelectAIMove(char ai_mark, AIDifficulty difficulty)
{
    if ((ai_mark != 'X' && ai_mark != 'O') || current_player != ai_mark ||
        Game_CheckStatus() != STATUS_ONGOING)
    {
        return -1;
    }
    if (difficulty == AI_EASY) return random_empty_square(game_board);
    if (difficulty == AI_MEDIUM) return medium_move(game_board, ai_mark);
    if (difficulty == AI_HARD) return hard_move(game_board, ai_mark);
    return -1;
}
