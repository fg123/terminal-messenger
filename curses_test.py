import curses
import string


def start(stdscr):
    stdscr.clear()
    stdscr.nodelay(True)
    stdscr.keypad(True)
    stdscr.refresh()
    while True:
        c = stdscr.getch(0, 0)
        show = None
        if c == -1: continue
        else:
            show = str(int(c))
        stdscr.move(0, 0)
        stdscr.clrtoeol()
        stdscr.addstr(0, 0, show)


curses.wrapper(start)