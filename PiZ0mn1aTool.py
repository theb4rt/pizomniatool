#!/usr/bin/env python

import time
from blessed import Terminal
from gpiozero import Button
from scaning import launch_scan
from scrollable_list import ScrollableList
from enum import Enum


class Key(Enum):
    JOYSTICK_CENTER = 3
    JOYSTICK_UP = 5
    JOYSTICK_RIGHT = 6
    JOYSTICK_DOWN = 16
    JOYSTICK_LEFT = 13
    BUTTON_SELECT = 26
    BUTTON_START = 19
    BUTTON_A = 21
    BUTTON_B = 20
    BUTTON_X = 15
    BUTTON_Y = 12
    BUTTON_R = 14
    BUTTON_L = 23


class Direction(Enum):
    UP = "up"
    RIGHT = "right"
    DOWN = "down"
    LEFT = "left"
    CENTER = "center"
    BACK = "back"
    SCROLL_UP = "scroll_up"
    SCROLL_DOWN = "scroll_down"


class Controls:
    def __init__(self):
        self.buttons = {
            Direction.UP: Button(Key.JOYSTICK_UP.value),
            Direction.RIGHT: Button(Key.JOYSTICK_RIGHT.value),
            Direction.DOWN: Button(Key.JOYSTICK_DOWN.value),
            Direction.LEFT: Button(Key.JOYSTICK_LEFT.value),
            Direction.CENTER: Button(Key.JOYSTICK_CENTER.value),
            Direction.BACK: Button(Key.BUTTON_L.value),
            Direction.SCROLL_UP: Button(Key.BUTTON_B.value),
            Direction.SCROLL_DOWN: Button(Key.BUTTON_A.value),
        }

    @property
    def direction(self):
        for direction, button in self.buttons.items():
            if button.is_pressed:
                return direction
        return None


class Menu(ScrollableList):
    def __init__(self, term, items, scrollable_items, controls, parent=None):
        super().__init__(term, scrollable_items)
        self.controls = controls
        self.term = term
        self.items = items
        self.selected_item = 0
        self.active_ips = []
        self.parent = parent

    def print_menu(self):
        self.clear_screen()
        with self.term.location(0, 0):
            title = f"""{self.term.bold_green}
    ┏━━━━━━━━━━━━━━━━━━━┓
    ┃    PiZ0mn1aTool   ┃
    ┗━━━━━━━━━━━━━━━━━━━┛
    {self.term.normal}"""
            print(self.term.center(title))
            print(self.term.center('-' * self.term.width))
            for i, item in enumerate(self.items):
                if i == self.selected_item:
                    print(self.term.center('-> ' + self.term.bold(item)))
                else:
                    print(self.term.center('   ' + item))
            print(self.term.center('-' * self.term.width))

    def clear_screen(self):
        print(self.term.clear)

    def move_selection(self, direction):
        if direction == Direction.UP.value:
            self.selected_item = max(0, self.selected_item - 1)
        elif direction == Direction.DOWN.value:
            self.selected_item = min(len(self.items) - 1, self.selected_item + 1)

    def execute_selected(self):
        if self.controls.direction == Direction.CENTER:
            self.clear_screen()
            if self.selected_item == 0:
                scan_data = launch_scan()
                active_ips = scan_data['active_ips']
                scan_list = scan_data['results']
                self.active_ips = active_ips
                iteration = 0
                self.scrollable_items.clear()
                for key, value in scan_list.items():
                    iteration += 1
                    ip = str(iteration) + ". " + self.term.green(key) + " -> "
                    os = self.term.yellow(value["os_type"] + ' - ') if value["os_type"] != "-" else ""
                    mac = self.term.cyan(value["mac_name"]) if value["mac_addr"] != "-" else " - "
                    self.scrollable_items.append(ip + os + mac)
                self.offset = 0
                self.print_scrollable_items()

            elif self.selected_item == 1:
                if not self.active_ips:
                    print("No active IPs, execute first option")
                    return

                ip_menu_items = [f"{idx + 1}. {ip}" for idx, ip in enumerate(self.active_ips)]
                ip_menu = IPMenu(self.term, ip_menu_items, [], self.controls, parent=self)
                ip_menu.active_ips = self.active_ips
                time.sleep(0.5)
                ip_menu.run()

                self.print_menu()

    def run(self):
        with self.term.fullscreen(), self.term.hidden_cursor():
            self.print_menu()
            while True:
                direction = self.controls.direction
                if direction:
                    if direction in [Direction.UP, Direction.DOWN]:
                        self.move_selection(direction.value)
                        self.print_menu()
                    elif direction == Direction.CENTER:
                        self.execute_selected()
                    elif direction == Direction.BACK:
                        if self.parent:
                            return
                        else:
                            self.clear_screen()
                            self.print_menu()
                    elif direction == Direction.SCROLL_UP or direction == Direction.SCROLL_DOWN:
                        self.clear_screen()
                        self.scroll(direction.value)
                time.sleep(0.1)


class IPMenu(Menu):

    # override "options" for avoid executing principal menu
    def execute_selected(self):
        if self.controls.direction == Direction.CENTER:
            self.clear_screen()
            selected_ip = self.active_ips[self.selected_item]
            scan_ip_menu = ScanIPMenu(self.term, [selected_ip], [], self.controls, parent=self)
            scan_ip_menu.run()

            self.print_menu()


class ScanIPMenu(Menu):

    def print_menu(self):
        print(f"Scanning selected IP: {self.items[0]}")

    # override "options" for avoid executing principal menu
    def execute_selected(self):
        if self.controls.direction == Direction.CENTER:
            print("Center button pressed, but there is no action defined in this context.")

    def run(self):
        with self.term.fullscreen(), self.term.hidden_cursor():
            self.print_menu()
            while True:
                direction = self.controls.direction
                if direction == Direction.BACK:
                    return
                time.sleep(0.1)


def main():
    term = Terminal()
    controls = Controls()
    menu_items = ["Scan Network", "Scan IP", "Option 3", "Option 4", "Option 5", "Option 6", "Option 7"]
    scrollable_items = []
    active_ips = []
    menu = Menu(term, menu_items, scrollable_items, controls, active_ips)
    menu.run()


if __name__ == "__main__":
    main()
