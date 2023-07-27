#!/usr/bin/env

import time

from blessed import Terminal
from gpiozero import Button
from scaning import launch_scan
import time

from scrollable_list import ScrollableList

KEY1 = 3  # Joystick center
KEY2 = 5  # Joystick up
KEY3 = 6  # Joystick right
KEY4 = 16  # Joystick down
KEY5 = 13  # Joystick left
KEY6 = 26  # Button Select
KEY7 = 19  # Button Start
KEY8 = 21  # Button A
KEY9 = 20  # Button B
KEY10 = 15  # Button X
KEY11 = 12  # Button Y
KEY12 = 14  # Button R
KEY13 = 23  # Button L


class Controls:
    def __init__(self):
        self.JOYSTICK_CENTER = Button(KEY1)
        self.JOYSTICK_UP = Button(KEY2)
        self.JOYSTICK_RIGHT = Button(KEY3)
        self.JOYSTICK_DOWN = Button(KEY4)
        self.JOYSTICK_LEFT = Button(KEY5)
        self.BUTTON_L = Button(KEY13)
        self.BUTTON_B = Button(KEY9)
        self.BUTTON_A = Button(KEY8)

    def get_direction(self):
        if self.JOYSTICK_UP.is_pressed:
            return "up"
        elif self.JOYSTICK_RIGHT.is_pressed:
            return "right"
        elif self.JOYSTICK_DOWN.is_pressed:
            return "down"
        elif self.JOYSTICK_LEFT.is_pressed:
            return "left"
        elif self.JOYSTICK_CENTER.is_pressed:
            return "center"
        elif self.BUTTON_L.is_pressed:
            return "back"
        elif self.BUTTON_B.is_pressed:
            return "scroll_up"
        elif self.BUTTON_A.is_pressed:
            return "scroll_down"
        else:
            return None


class Menu(ScrollableList):
    def __init__(self, term, items, scrollable_items):
        super().__init__(term, scrollable_items)
        self.term = term
        self.items = items
        self.selected_item = 0
        self.controls = Controls()

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
        # print(self.term.center('Navigate with the joystick. Select with center. Back with Button L'))

    def clear_screen(self):
        print(self.term.clear)

    def move_selection(self, direction):
        if direction == "up":
            self.selected_item = max(0, self.selected_item - 1)
        elif direction == "down":
            self.selected_item = min(len(self.items) - 1, self.selected_item + 1)

    def execute_selected(self):
        if self.controls.get_direction() == "center":
            self.clear_screen()
            if self.selected_item == 0:
                scan_list = launch_scan()
                iteration = 0
                self.scrollable_items.clear()
                for key, value in scan_list.items():
                    iteration += 1
                    ip = str(iteration) + ". " + key + " -> "
                    os = value["os_type"] + ' - ' if value["os_type"] != "-" else ""
                    mac = value["mac_name"] if value["mac_addr"] != "-" else " - "
                    self.scrollable_items.append(ip + os + mac)
                self.offset = 0
                self.print_scrollable_items()

    def run(self):
        with self.term.fullscreen(), self.term.hidden_cursor():
            self.print_menu()
            while True:
                direction = self.controls.get_direction()
                if direction:
                    if direction in ["up", "down"]:
                        self.move_selection(direction)
                        self.print_menu()
                    elif direction == "center":
                        self.execute_selected()
                    elif direction == "back":
                        self.clear_screen()
                        self.print_menu()
                    elif direction == "scroll_up" or direction == "scroll_down":
                        self.clear_screen()
                        self.scroll(direction)
                time.sleep(0.1)


def main():
    term = Terminal()
    menu_items = ["Scan Network", "Option 2", "Option 3", "Option 4", "Option 5", "Option 6", "Option 7"]
    scrollable_items = []
    menu = Menu(term, menu_items, scrollable_items)
    menu.run()


if __name__ == "__main__":
    main()
