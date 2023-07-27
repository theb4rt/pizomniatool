class ScrollableList:

    def __init__(self, term, scrollable_items):
        self.term = term
        self.scrollable_items = scrollable_items
        self.offset = 0
        self.display_lines = 4

    def print_scrollable_items(self):
        print("\n")
        for i in range(self.offset, min(self.offset + self.display_lines, len(self.scrollable_items))):
            print(self.scrollable_items[i] + "\n")

    def scroll(self, direction):
        if direction == "scroll_up":
            self.offset = max(0, self.offset - 1)
            self.print_scrollable_items()
        elif direction == "scroll_down":
            self.offset = min(len(self.scrollable_items) - self.display_lines, self.offset + 1)
            self.print_scrollable_items()
