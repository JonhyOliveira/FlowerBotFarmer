import curses
from typing import Union


class Nav(object):

    def show(self):
        pass

    def start(self, starting_menu):
        pass

    def navigate_up(self):
        pass

    def navigate_down(self):
        pass

    def navigate_down_to(self, menu):
        pass


class Menu(object):

    def __init__(self, terminal_screen: curses.window, title=None):
        self.terminal = terminal_screen
        self.title = title

    def show(self, n: Nav):
        pass


class Navigation(Nav):

    def __init__(self, starting_menu: Menu):
        self.back_stack: list[Menu] = []
        self.front_stack: list[Menu] = []
        self.currentMenu = starting_menu

    def show(self):
        self.currentMenu.show(self)

    def navigate_up(self):
        if len(self.back_stack):
            m = self.back_stack.pop()
            self.front_stack.append(m)
            self.currentMenu = m
        else:
            exit(5)

    def navigate_down(self):
        if len(self.front_stack):
            m = self.front_stack.pop()
            self.back_stack.append(self.currentMenu)
            self.currentMenu = m

    def navigate_down_to(self, menu: Menu):
        self.front_stack.clear()
        self.front_stack.append(menu)
        self.navigate_down()


class TerminalMenu(Menu):

    def __init__(self, terminal_screen: curses.window, m_choices: dict[str, Union[tuple, Menu]] = None, title=None):
        super(TerminalMenu, self).__init__(terminal_screen, title)
        self.choices = m_choices

    def show(self, n: Navigation):

        if self.title:
            self.terminal.addstr(
                min(max(curses.LINES//4, 0), curses.LINES - 1),
                min(max(curses.COLS//2 - len(self.title)//2, 0), curses.COLS - 1 - len(self.title)),
                self.title,
                curses.color_pair(1) | curses.A_UNDERLINE | curses.A_BOLD
            )

        choices = {}

        for i, (m_choice, func) in enumerate(self.choices.items()):
            prefix = f"{i+1}. "
            text = f"{prefix}{m_choice}"
            self.terminal.addstr(
                min(max(curses.LINES//2 + i, 0), curses.LINES - 1),
                min(max((curses.COLS//2 - len(m_choice)//2) - len(prefix), 0), curses.COLS - 1 - len(text)),
                text
            )

            choices.update({i+1: func})

        back = "Press [BackSpace] to go back"
        self.terminal.addstr(
            min(max(curses.LINES - 3, 0), curses.LINES - 1),
            min(3, curses.COLS - 1 - len(back)),
            back
        )

        if chr(choice := self.terminal.getch()).isnumeric():
            if (choice := int(chr(choice))) in choices.keys():
                c = choices[choice]
                if isinstance(c, tuple):
                    if c[1] is not None:
                        c[0](c[1])
                    else:
                        c[0]()

                elif isinstance(c, Menu):
                    n.navigate_down_to(c)

        elif choice == 8:  # backspace
            n.navigate_up()



