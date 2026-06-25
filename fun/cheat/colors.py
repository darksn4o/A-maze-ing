"""Block 5 - Colours: ANSI palette for the overlay markers.

Raw ANSI escape sequences used by the renderer to tint the obstacle, entry,
exit and solved-path markers, plus the reset code that ends a coloured run.
"""

# TEMP: ANSI colours used to draw the overlay markers.
LABEL_COLOR: str = "\033[34m"        # "42" obstacle (deep blue)
ENTRY_COLOR: str = "\033[32m"        # entry block (green)
EXIT_COLOR: str = "\033[31m"         # exit block (red)
PATH_COLOR: str = "\033[38;5;208m"   # solved path (orange)
COLOR_RESET: str = "\033[0m"
