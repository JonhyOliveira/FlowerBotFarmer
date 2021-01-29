from curses.textpad import rectangle
from botAPI import WateringCan, Plant
from navigation import Menu, TerminalMenu, Navigation, Nav
import threading
import toml
import time
import logging
import random
import os
import platform
import curses

clear_terminal = os.system("cls") if platform.system() == 'Windows' else os.system("clear")


def string_progressbar(iteration, total, prefix='', suffix='', decimals=1, length=100, fill='█'):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
        printEnd    - Optional  : end character (e.g. "\r", "\r\n") (Str)
    """
    iteration = min(iteration, total)
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)

    return f'{prefix}|{bar}| {percent}% {suffix}'
    # Print New Line on Complete
    # if iteration == total:
    #    print()


class PlantWorker(threading.Thread, Menu):
    global wc
    global exit_event

    def __init__(self, t_plant: Plant, terminal: curses.window):
        super(PlantWorker, self).__init__(daemon=True)
        self.terminal = terminal
        self.plant = t_plant
        self.log = logging.getLogger(f"{__name__}.{t_plant.name}")
        self.sleep_time = 1
        self.start_sleep = time.time()

    def run(self) -> None:

        while not exit_event.is_set():
            result = wc.water_plant(self.plant.name)
            # set cooldown
            if result[0]:
                self.plant.level = min(self.plant.level + 1, self.plant.max_level)
                self.sleep_time = random.randint(15 * 60,
                                                 16 * 60 + 30)  # random between 15 and 16.5 minutes (plant cooldown)
            else:
                self.sleep_time = result[1].tm_min * 60 + result[1].tm_sec + 1
            self.start_sleep = time.time()

            self.log.debug(f"watering: success={result[0]} waiting {self.sleep_time} seconds")

            # wait for cooldown
            while not exit_event.is_set() and time.time() <= self.start_sleep + self.sleep_time:
                time.sleep(1)

    def show(self, n: Navigation):
        # plant info
        text = "Name:"
        self.terminal.addstr(
            min(max(curses.LINES // 10, 0), curses.LINES - 1),
            min(max(curses.COLS // 10, 0), curses.COLS - 1 - len(text)),
            text,
            curses.color_pair(1) | curses.A_BOLD
        )

        p_name = self.plant.name
        self.terminal.addstr(
            min(max(curses.LINES // 10, 0), curses.LINES - 1),
            min(max(curses.COLS // 10 + len(text) + 1, 0), curses.COLS - 1 - len(p_name)),
            p_name
        )

        text = "Type:"
        self.terminal.addstr(
            min(max(curses.LINES // 10 + 1, 0), curses.LINES - 1),
            min(max(curses.COLS // 10, 0), curses.COLS - 1 - len(text)),
            text,
            curses.color_pair(1) | curses.A_BOLD
        )

        p_type = self.plant.type
        self.terminal.addstr(
            min(max(curses.LINES // 10 + 1, 0), curses.LINES - 1),
            min(max(curses.COLS // 10 + len(text) + 1, 0), curses.COLS - 1 - len(p_type)),
            p_type
        )

        text = "Nourishment Level:"
        self.terminal.addstr(
            min(max(curses.LINES // 10 + 2, 0), curses.LINES - 1),
            min(max(curses.COLS // 10, 0), curses.COLS - 1 - len(text)),
            text,
            curses.color_pair(1) | curses.A_BOLD
        )

        p_lvl = f"{self.plant.level}/{self.plant.max_level}"
        self.terminal.addstr(
            min(max(curses.LINES // 10 + 2, 0), curses.LINES - 1),
            min(max(curses.COLS // 10 + len(text) + 1, 0), curses.COLS - 1 - len(p_lvl)),
            p_lvl
        )

        text = "Cooldown:"
        self.terminal.addstr(
            min(max(curses.LINES // 10 + 4, 0), curses.LINES - 1),
            min(max(curses.COLS // 10, 0), curses.COLS - 1 - len(text)),
            text,
            curses.color_pair(1) | curses.A_BOLD | curses.A_UNDERLINE
        )

        time_left = self.start_sleep + self.sleep_time - time.time()

        p_cooldown = string_progressbar(time.time() - self.start_sleep, self.sleep_time,
                                        suffix=f" {int(time_left)} seconds left ({int(time_left//60)} "
                                               f"minutes and {int(time_left%60)} seconds)",
                                        length=curses.COLS // 3)

        self.terminal.addstr(
            min(max(curses.LINES // 10 + 6, 0), curses.LINES - 1),
            min(max(curses.COLS // 10, 0), curses.COLS - 1 - len(p_cooldown)),
            p_cooldown
        )

        back = "Press [BackSpace] to go back"
        self.terminal.addstr(
            min(max(curses.LINES - 3, 0), curses.LINES - 1),
            min(3, curses.COLS - 1 - len(back)),
            back
        )

        if self.terminal.getch() == 8:
            n.navigate_up()


class PlantTracker(TerminalMenu):
    global threads

    def __init__(self, terminal_screen: curses.window):
        self.choices = {f"{thread.plant.name} ({thread.plant.type})": thread for thread in threads}
        super(PlantTracker, self).__init__(terminal_screen, self.choices, "Plant Tracker")

    def show(self, n: Navigation):
        self.choices = {f"{thread.plant.name} ({thread.plant.type})": thread for thread in threads}
        super(PlantTracker, self).show(n)


class InfoScreen(Menu):
    global wc

    def __init__(self, terminal_screen: curses.window):
        super(InfoScreen, self).__init__(terminal_screen, "Info")

    def show(self, n: Nav):

        back = "Press [BackSpace] to go back"
        self.terminal.addstr(
            min(max(curses.LINES - 3, 0), curses.LINES - 1),
            min(3, curses.COLS - 1 - len(back)),
            back
        )

        self.terminal.refresh()

        text = "EXP:"
        self.terminal.addstr(
            min(max(curses.LINES // 10, 0), curses.LINES - 1),
            min(max(curses.COLS // 10, 0), curses.COLS - 1 - len(text)),
            text,
            curses.color_pair(1) | curses.A_BOLD
        )

        u_exp = str(wc.get_exp())
        self.terminal.addstr(
            min(max(curses.LINES // 10, 0), curses.LINES - 1),
            min(max(curses.COLS // 10 + len(text) + 1, 0), curses.COLS - 1 - len(u_exp)),
            u_exp
        )

        if self.terminal.getch() == 8:  # backspace
            n.navigate_up()


def setup_logging():
    logging.basicConfig(format='%(levelname)s[%(name)s:%(funcName)s at %(asctime)s] %(message)s',
                        datefmt='%m/%d/%y %I:%M:%S %p')

    log = logging.getLogger(__name__)

    log.setLevel(logging.WARNING)


def get_config() -> dict:
    with open("config.toml", "r") as f:
        return toml.load(f)


def setup_curses_terminal() -> curses.window:
    # setup terminal window
    stdscr = curses.initscr()
    stdscr.keypad(True)

    curses.noecho()
    curses.cbreak()
    curses.start_color()

    # set color
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)

    return stdscr


if __name__ == '__main__':
    setup_logging()
    config = get_config()

    # setup watering can
    print("Setting up watering can..")
    wc = WateringCan(config["token"], config["channelID"])
    print(plants := wc.get_plants())

    # workers
    exit_event = threading.Event()
    exit_event.clear()

    threads = []

    print("Creating threads...")
    for plant in plants:
        threads.append(PlantWorker(plant, None))

    for thread in threads:
        print(f"Starting \"{thread.plant.name}\"s thread..")
        time.sleep(.5)
        thread.start()

    # setup navigation
    plant_tracker = PlantTracker(None)
    info_screen = InfoScreen(None)
    main_menu = TerminalMenu(None, {
        plant_tracker.title: plant_tracker,
        info_screen.title: info_screen
    }, "Main Menu")
    print({thread.plant.name: thread for thread in threads})

    nav = Navigation(main_menu)

    print("Setting up terminal UI")
    time.sleep(.2)
    # setup terminal
    stdscr = setup_curses_terminal()

    main_menu.terminal = stdscr
    plant_tracker.terminal = stdscr
    info_screen.terminal = stdscr
    for thread in threads:
        thread.terminal = stdscr

    while True:
        rectangle(stdscr, 0, 0, curses.LINES - 2, curses.COLS - 2)

        tooltip = "Press any key to update view"
        stdscr.addstr(
            curses.LINES - 3,
            curses.COLS - 3 - len(tooltip),
            tooltip,
            curses.A_STANDOUT
        )
        nav.show()

        stdscr.refresh()
        time.sleep(.1)
        stdscr.clear()
