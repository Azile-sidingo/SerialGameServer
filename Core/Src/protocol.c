/* protocol.c */
#include "protocol.h"
#include "game.h"
#include <string.h>
#include <stdio.h>

ServerState current_state = STATE_IDLE;
static char match_result = '\0'; /* Caches 'X', 'O', or 'D' when a game ends */

void Protocol_ParseCommand(const char *command, char *response)
{
    /* Default fallback for any command not explicitly authorized in the current state */
    strcpy(response, RSP_NACK_BADCMD);

    if (current_state == STATE_IDLE)
    {
        /* IDLE: responds to CONNECT, NEW, and STATE */
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
            Game_Init();
            current_state = STATE_IN_PROGRESS;
            match_result = '\0'; /* Reset cache for the new game */
            sprintf(response, "OK: BOARD:%s\r\n", game_board);
        }
        else if (strncmp(command, CMD_MOVE_PREFIX, strlen(CMD_MOVE_PREFIX)) == 0 || strcmp(command, CMD_RESIGN) == 0)
        {
            strcpy(response, RSP_NACK_NOGAME);
        }
    }
    else if (current_state == STATE_IN_PROGRESS)
    {
        /* IN_PROGRESS: responds to MOVE, STATE, RESIGN, and NEW */
        if (strcmp(command, CMD_NEW) == 0)
        {
            Game_Init();
            current_state = STATE_IN_PROGRESS;
            match_result = '\0';
            sprintf(response, "OK: BOARD:%s\r\n", game_board);
        }
        else if (strcmp(command, CMD_STATE) == 0)
        {
            sprintf(response, "OK: BOARD:%s GAME IN_PROGRESS\r\n", game_board);
        }
        else if (strcmp(command, CMD_RESIGN) == 0)
        {
            char winner = (current_player == 'X') ? 'O' : 'X';
            current_state = STATE_GAME_OVER;
            match_result = winner; /* Cache the winner by resignation */
            sprintf(response, "OK: BOARD:%s WIN:%c\r\n", game_board, winner);
        }
        else if (strncmp(command, CMD_MOVE_PREFIX, strlen(CMD_MOVE_PREFIX)) == 0)
        {
            int move_index;
            if (sscanf(command, "MOVE:%d", &move_index) == 1)
            {
                MoveResult result = Game_ApplyMove(move_index);
                if (result == MOVE_OK)
                {
                    GameStatus status = Game_CheckStatus();
                    if (status == STATUS_ONGOING)
                    {
                        sprintf(response, "OK: BOARD:%s\r\n", game_board);
                    }
                    else
                    {
                        current_state = STATE_GAME_OVER;
                        if (status == STATUS_WIN_X)
                        {
                            match_result = 'X'; /* Cache physical win */
                            sprintf(response, "OK: BOARD:%s WIN:X\r\n", game_board);
                        }
                        else if (status == STATUS_WIN_O)
                        {
                            match_result = 'O'; /* Cache physical win */
                            sprintf(response, "OK: BOARD:%s WIN:O\r\n", game_board);
                        }
                        else if (status == STATUS_DRAW)
                        {
                            match_result = 'D'; /* Cache draw */
                            sprintf(response, "OK: BOARD:%s DRAW\r\n", game_board);
                        }
                    }
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
        /* GAME_OVER: responds to NEW, STATE, and DISCONNECT */
        if (strcmp(command, CMD_NEW) == 0)
        {
            Game_Init();
            current_state = STATE_IN_PROGRESS;
            match_result = '\0';
            sprintf(response, "OK: BOARD:%s\r\n", game_board);
        }
        else if (strcmp(command, CMD_DISCONNECT) == 0)
        {
            current_state = STATE_IDLE;
            match_result = '\0';
            strcpy(response, RSP_OK);
        }
        else if (strcmp(command, CMD_STATE) == 0)
        {
            /* Rely on the cached result instead of evaluating the physical grid */
            if (match_result == 'X' || match_result == 'O')
            {
                sprintf(response, "OK: BOARD:%s GAME_OVER WIN:%c\r\n", game_board, match_result);
            }
            else
            {
                sprintf(response, "OK: BOARD:%s GAME_OVER DRAW\r\n", game_board);
            }
        }
        else if (strncmp(command, CMD_MOVE_PREFIX, strlen(CMD_MOVE_PREFIX)) == 0 || strcmp(command, CMD_RESIGN) == 0)
        {
            strcpy(response, RSP_NACK_NOGAME);
        }
    }
}
