/* protocol.c -- Authoritative STM32 game state and UART command handling. */
#include "protocol.h"
#include "game.h"
#include <string.h>
#include <stdio.h>

ServerState current_state = STATE_IDLE;
static char match_result = '\0'; /* Existing cache: 'X', 'O', or 'D'. */

typedef enum {
    GAME_MODE_PVP,
    GAME_MODE_AI
} GameMode;

/* MODE changes the NEXT round only, not an active match. */
static GameMode configured_mode = GAME_MODE_PVP;
static GameMode active_mode = GAME_MODE_PVP;
static AIDifficulty configured_difficulty = AI_MEDIUM;
static AIDifficulty active_difficulty = AI_MEDIUM;
static char configured_ai_mark = 'O';
static char active_ai_mark = 'O';

/* Assign the winner/draw once; the legacy wire response is unchanged. */
static void write_board_response(char *response)
{
    GameStatus status = Game_CheckStatus();
    if (status == STATUS_ONGOING)
    {
        sprintf(response, "OK: BOARD:%s\r\n", game_board);
        return;
    }

    current_state = STATE_GAME_OVER;
    if (status == STATUS_WIN_X)
    {
        match_result = 'X';
        sprintf(response, "OK: BOARD:%s WIN:X\r\n", game_board);
    }
    else if (status == STATUS_WIN_O)
    {
        match_result = 'O';
        sprintf(response, "OK: BOARD:%s WIN:O\r\n", game_board);
    }
    else
    {
        match_result = 'D';
        sprintf(response, "OK: BOARD:%s DRAW\r\n", game_board);
    }
}

/* Invoked immediately after the human move (or NEW when AI plays X).
 * Game_ApplyMove remains the only way that ANY mark reaches game_board. */
static void play_ai_if_needed(void)
{
    if (active_mode != GAME_MODE_AI ||
        current_state != STATE_IN_PROGRESS ||
        current_player != active_ai_mark ||
        Game_CheckStatus() != STATUS_ONGOING)
    {
        return;
    }
    int index = Game_SelectAIMove(active_ai_mark, active_difficulty);
    if (index >= 0)
    {
        (void)Game_ApplyMove(index);
    }
}

static void begin_new_game(char *response)
{
    active_mode = configured_mode;
    active_difficulty = configured_difficulty;
    active_ai_mark = configured_ai_mark;

    Game_Init();
    current_state = STATE_IN_PROGRESS;
    match_result = '\0';
    play_ai_if_needed();
    write_board_response(response);
}

/* The extra MODE command is optional to older clients and does not affect
 * CONNECT / NEW / MOVE / STATE / RESIGN / DISCONNECT responses. */
static int set_next_mode(const char *command, char *response)
{
    if (strcmp(command, "MODE:PVP") == 0)
    {
        configured_mode = GAME_MODE_PVP;
    }
    else if (strcmp(command, "MODE:AI:EASY:X") == 0 ||
             strcmp(command, "MODE:AI:EASY:O") == 0)
    {
        configured_mode = GAME_MODE_AI;
        configured_difficulty = AI_EASY;
        configured_ai_mark = command[strlen(command) - 1];
    }
    else if (strcmp(command, "MODE:AI:MEDIUM:X") == 0 ||
             strcmp(command, "MODE:AI:MEDIUM:O") == 0)
    {
        configured_mode = GAME_MODE_AI;
        configured_difficulty = AI_MEDIUM;
        configured_ai_mark = command[strlen(command) - 1];
    }
    else if (strcmp(command, "MODE:AI:HARD:X") == 0 ||
             strcmp(command, "MODE:AI:HARD:O") == 0)
    {
        configured_mode = GAME_MODE_AI;
        configured_difficulty = AI_HARD;
        configured_ai_mark = command[strlen(command) - 1];
    }
    else
    {
        return 0;
    }
    strcpy(response, RSP_OK);
    return 1;
}

void Protocol_ParseCommand(const char *command, char *response)
{
    strcpy(response, RSP_NACK_BADCMD);

    /* Configuration is accepted in any state but takes effect on NEW only. */
    if (strncmp(command, "MODE:", 5) == 0)
    {
        (void)set_next_mode(command, response);
        return;
    }

    if (current_state == STATE_IDLE)
    {
        if (strcmp(command, CMD_CONNECT) == 0)
        {
            strcpy(response, RSP_OK);
        }
        else if (strcmp(command, CMD_STATE) == 0)
        {
            sprintf(response, "OK: IDLE\r\n");
        }
        else if (strcmp(command, CMD_NEW) == 0)
        {
            begin_new_game(response);
        }
        else if (strncmp(command, CMD_MOVE_PREFIX, strlen(CMD_MOVE_PREFIX)) == 0 ||
                 strcmp(command, CMD_RESIGN) == 0)
        {
            strcpy(response, RSP_NACK_NOGAME);
        }
    }
    else if (current_state == STATE_IN_PROGRESS)
    {
        if (strcmp(command, CMD_NEW) == 0)
        {
            begin_new_game(response);
        }
        else if (strcmp(command, CMD_STATE) == 0)
        {
            sprintf(response, "OK: BOARD:%s GAME IN_PROGRESS\r\n", game_board);
        }
        else if (strcmp(command, CMD_RESIGN) == 0)
        {
            char winner = (current_player == 'X') ? 'O' : 'X';
            current_state = STATE_GAME_OVER;
            match_result = winner;
            sprintf(response, "OK: BOARD:%s WIN:%c\r\n", game_board, winner);
        }
        else if (strncmp(command, CMD_MOVE_PREFIX, strlen(CMD_MOVE_PREFIX)) == 0)
        {
            int index;
            if (sscanf(command, "MOVE:%d", &index) == 1)
            {
                /* After each returned AI move it is again the human turn. */
                if (active_mode == GAME_MODE_AI && current_player == active_ai_mark)
                {
                    strcpy(response, RSP_NACK_BADCMD);
                    return;
                }
                MoveResult result = Game_ApplyMove(index);
                if (result == MOVE_OK)
                {
                    play_ai_if_needed();
                    write_board_response(response);
                }
                else if (result == MOVE_OUT_OF_RANGE)
                {
                    strcpy(response, RSP_NACK_RANGE);
                }
                else if (result == MOVE_OCCUPIED)
                {
                    strcpy(response, RSP_NACK_OCCUPIED);
                }
            }
        }
    }
    else if (current_state == STATE_GAME_OVER)
    {
        if (strcmp(command, CMD_NEW) == 0)
        {
            begin_new_game(response);
        }
        else if (strcmp(command, CMD_DISCONNECT) == 0)
        {
            current_state = STATE_IDLE;
            match_result = '\0';
            strcpy(response, RSP_OK);
        }
        else if (strcmp(command, CMD_STATE) == 0)
        {
            if (match_result == 'X' || match_result == 'O')
            {
                sprintf(response, "OK: BOARD:%s GAME_OVER WIN:%c\r\n",
                        game_board, match_result);
            }
            else
            {
                sprintf(response, "OK: BOARD:%s GAME_OVER DRAW\r\n", game_board);
            }
        }
        else if (strncmp(command, CMD_MOVE_PREFIX, strlen(CMD_MOVE_PREFIX)) == 0 ||
                 strcmp(command, CMD_RESIGN) == 0)
        {
            strcpy(response, RSP_NACK_NOGAME);
        }
    }
}
