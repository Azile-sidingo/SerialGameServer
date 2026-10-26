#ifndef LCD_STATUS_H
#define LCD_STATUS_H

#include "protocol.h"

/* Small, read-only LCD view of the embedded server state. */
void LCD_Status_Init(void);
void LCD_Status_Update(ServerState state);

#endif /* LCD_STATUS_H */
