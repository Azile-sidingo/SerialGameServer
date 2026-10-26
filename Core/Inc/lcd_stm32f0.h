#ifndef LCD_STM32F0_H
#define LCD_STM32F0_H

/* UCT STM32F0 LCD driver declarations and original GPIO bit masks.
 * Matched to lcd_stm32f0.c (R. Verrinder / J. Gowans version).
 *
 * Pin mapping (4-bit HD44780 interface):
 *   RS -> PC14; E -> PC15;
 *   D4 -> PB8; D5 -> PB9; D6 -> PA12; D7 -> PA15.
 *
 * The driver writes GPIOx->BSRR: lower 16 bits SET a pin,
 * upper 16 bits RESET a pin. Identical bit masks on DIFFERENT
 * GPIO ports are intentional (for example PC15 and PA15).
 */
#include "stm32f0xx.h"

#define CLEAR           0x01U
#define CURSOR_HOME     0x02U
#define DISPLAY_ON      0x0CU
#define DISPLAY_OFF     0x08U
#define LINE_TWO        0xC0U
#define POWER_UP        0x33U
#define FOURBIT_MODE    0x32U
#define TWOLINE_MODE    0x28U

#define LCD_RS_SET      (1UL << 14)
#define LCD_RS_RESET    (1UL << (14 + 16))
#define LCD_EN_SET      (1UL << 15)
#define LCD_EN_RESET    (1UL << (15 + 16))

#define LCD_D4_SET      (1UL << 8)
#define LCD_D4_RESET    (1UL << (8 + 16))
#define LCD_D5_SET      (1UL << 9)
#define LCD_D5_RESET    (1UL << (9 + 16))
#define LCD_D6_SET      (1UL << 12)
#define LCD_D6_RESET    (1UL << (12 + 16))
#define LCD_D7_SET      (1UL << 15)
#define LCD_D7_RESET    (1UL << (15 + 16))

#define DELAY_COUNT     0x1FFU

void init_LCD(void);
void lcd_command(unsigned char command);
void lcd_putchar(unsigned char character);
void lcd_putstring(char *instring);
void delay(unsigned int microseconds);
void pulse_strobe(void);

#endif /* LCD_STM32F0_H */
