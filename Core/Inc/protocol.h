#ifndef PROTOCOL_H
#define PROTOCOL_H

/* UART protocol; kept compatible with the uploaded GUI's command vocabulary. */
#define CMD_CONNECT       "CONNECT"
#define CMD_DISCONNECT    "DISCONNECT"
#define CMD_NEW           "NEW"
#define CMD_STATE         "STATE"
#define CMD_RESIGN        "RESIGN"
#define CMD_MOVE_PREFIX   "MOVE:"
#define CMD_MODE_PREFIX   "MODE:"

#define RSP_OK             "OK\r\n"
#define RSP_NACK_BADCMD    "NACK: BADCMD\r\n"
#define RSP_NACK_NOGAME    "NACK: NOGAME\r\n"
#define RSP_NACK_RANGE     "NACK: RANGE\r\n"
#define RSP_NACK_OCCUPIED  "NACK: OCCUPIED\r\n"

typedef enum {
    STATE_IDLE,
    STATE_IN_PROGRESS,
    STATE_GAME_OVER
} ServerState;

extern ServerState current_state;
void Protocol_ParseCommand(const char *command, char *response);

#endif
