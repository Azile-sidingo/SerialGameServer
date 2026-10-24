/* protocol.h */
#ifndef PROTOCOL_H
#define PROTOCOL_H

#include <stdint.h>

/* --- Incoming Commands --- */
#define CMD_CONNECT    "CONNECT"
#define CMD_NEW        "NEW"
#define CMD_STATE      "STATE"
#define CMD_RESIGN     "RESIGN"
#define CMD_DISCONNECT "DISCONNECT"
/* Note: The MOVE command includes arguments (e.g., "MOVE:4"),
   so we will define a prefix for it later when we build the parser. */
#define CMD_MOVE_PREFIX "MOVE:"

/* --- Outgoing Responses --- */
#define RSP_OK              "OK\r\n"
#define RSP_NACK_BADCMD     "NACK: BADCMD\r\n"
#define RSP_NACK_NOGAME     "NACK: NOGAME\r\n"
#define RSP_NACK_OCCUPIED   "NACK: OCCUPIED\r\n"
#define RSP_NACK_RANGE      "NACK: RANGE\r\n"
#define RSP_NACK_NOTURN     "NACK: NOTURN\r\n"

/* The three compulsory server states */
typedef enum {
    STATE_IDLE,
    STATE_IN_PROGRESS,
    STATE_GAME_OVER
} ServerState;

/* Expose the state so other files can read it */
extern ServerState current_state;

/* Parses the incoming command string and populates the response string */
void Protocol_ParseCommand(const char *command, char *response);

#endif /* PROTOCOL_H */
