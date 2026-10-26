/* STM32-only view of the authoritative protocol state.
 * All C game logic, AI moves and UART response handling remain unchanged.
 * Requires the matching UCT lcd_stm32f0.c / lcd_stm32f0.h driver pair.
 */
#include "lcd_status.h"
#include "lcd_stm32f0.h"

#define LCD_COLUMNS 16U

/* -1 ensures the first status update always writes to the screen. */
static int last_displayed_state = -1;

/* Clear remaining characters when the next message is shorter. */
static void LCD_Status_WriteLine(const char *message)
{
    char line[LCD_COLUMNS + 1U];
    unsigned int i = 0U;

    while (i < LCD_COLUMNS && message[i] != '\0')
    {
        line[i] = message[i];
        ++i;
    }
    while (i < LCD_COLUMNS)
    {
        line[i++] = ' ';
    }
    line[LCD_COLUMNS] = '\0';
    lcd_putstring(line);
}

void LCD_Status_Init(void)
{
    init_LCD();
    last_displayed_state = -1;
}

void LCD_Status_Update(ServerState state)
{
    const char *label;

    /* Avoid redrawing (and delaying UART handling) for unchanged state. */
    if ((int)state == last_displayed_state)
        return;

    switch (state)
    {
        case STATE_IDLE:        label = "IDLE";        break;
        case STATE_IN_PROGRESS: label = "IN_PROGRESS"; break;
        case STATE_GAME_OVER:   label = "GAME_OVER";   break;
        default: return;
    }

    lcd_command(CURSOR_HOME);
    LCD_Status_WriteLine("SERVER STATE");
    lcd_command(LINE_TWO);
    LCD_Status_WriteLine(label);
    last_displayed_state = (int)state;
}
