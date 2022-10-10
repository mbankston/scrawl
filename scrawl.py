import curses
from sys import exit
import argparse
from dataclasses import dataclass, field


@dataclass
class TextBuffer:
    filename: str
    lines: list[str] = field(default_factory=list)

    def __len__(self):
        return len(self.lines)

    def __getitem__(self, i):
        return self.lines[i]

    @property
    def last_row(self):
        return len(self) - 1

    def write(self, cursor, user_input):
        current_line = self.lines.pop(cursor.row) if self.lines else ''
        new_text = current_line[: cursor.col] + user_input + current_line[cursor.col:]
        self.lines.insert(cursor.row, new_text)

    def line_break(self, cursor):
        current_line = self.lines.pop(cursor.row)
        self.lines.insert(cursor.row, current_line[: cursor.col])
        self.lines.insert(cursor.row + 1, current_line[cursor.col:])

    def delete(self, cursor):
        if (cursor.row, cursor.col) < (self.last_row, len(self[cursor.row])):
            current_line = self.lines.pop(cursor.row)
            if cursor.col < len(self[cursor.row]):
                new = current_line[: cursor.col] + current_line[cursor.col + 1:]
                self.lines.insert(cursor.row, new)
            else:
                next_line = self.lines.pop(cursor.row)
                new = current_line + next_line
                self.lines.insert(cursor.row, new)

    def save(self):
        with open(self.filename, 'w') as fw:
            for i, line in enumerate(self.lines):
                if i == 0:
                    fw.write(line)
                else:
                    fw.write('\n'+line)
            fw.close()


@dataclass
class Cursor:
    row: int = 0
    _col = 0
    last_known_col = None
    _last_known_col = _col if last_known_col is None else last_known_col

    @property
    def col(self) -> int:
        return self._col

    @col.setter
    def col(self, v) -> None:
        self._col = v
        self._last_known_col = v

    def move_up(self, buffer):
        self.row -= 1 if self.row > 0 else self.row
        self._adjust_cursor_float(buffer)

    def move_down(self, buffer):
        if self.row < buffer.last_row:
            self.row += 1
            self._adjust_cursor_float(buffer)

    def move_left(self, buffer):
        if self.col > 0:
            self.col -= 1
        elif self.row > 0:
            self.row -= 1
            self.col = len(buffer[self.row])

    def move_right(self, buffer):
        if self.col < len(buffer[self.row]):
            self.col += 1
        elif self.row < buffer.last_row:
            self.row += 1
            self.col = 0

    def _adjust_cursor_float(self, buffer):
        self._col = min(self._last_known_col, len(buffer[self.row]))


@dataclass
class Window:
    row_count: int
    col_count: int
    current_row: int = 0
    current_col: int = 0

    def place_cursor_in_window(self, cursor):
        return cursor.row - self.current_row, cursor.col - self.current_col

    @property
    def last_row(self):
        return self.current_row + self.row_count - 1

    def up(self, cursor: Cursor):
        if cursor.row == self.current_row - 1 and self.current_row > 0:
            self.current_row -= 1

    def down(self, cursor: Cursor, buffer: TextBuffer):
        if cursor.row == self.last_row + 1 and self.last_row < buffer.last_row:
            self.current_row += 1

    def horizontal_scroll(self, cursor):
        left_margin = 5
        right_margin = 2
        pages_length = cursor.col // (self.col_count - right_margin)
        self.current_col = max(
            pages_length * self.col_count - right_margin - left_margin, 0
        )


def get_filename_arg():
    parser = argparse.ArgumentParser()
    parser.add_argument("filename")

    args = parser.parse_args()
    return args.filename


def editor(stdscr: curses.window):
    filename = get_filename_arg()

    window = Window(curses.LINES - 1, curses.COLS - 1)

    with open(filename) as f:
        buffer = TextBuffer(lines=f.read().splitlines(),filename=filename)

    cursor = Cursor()

    while True:
        stdscr.clear()

        for row, line in enumerate(
            buffer[window.current_row: window.current_row + window.row_count]
        ):
            if row == cursor.row - window.current_row and window.current_col > 0:
                line = "↞" + line[window.current_col + 1:]
            if len(line) > window.col_count:
                line = line[: window.col_count - 1] + "↠"
            stdscr.addstr(row, 0, line)
        stdscr.move(*window.place_cursor_in_window(cursor))
        # listen for key input
        key = stdscr.getkey()
        read_key_input(key, cursor, window, buffer)


def right(cursor, window, buffer):
    cursor.move_right(buffer)
    window.down(cursor, buffer)
    window.horizontal_scroll(cursor)


def left(cursor, window, buffer):
    cursor.move_left(buffer)
    window.up(cursor)
    window.horizontal_scroll(cursor)


def read_key_input(key, cursor, window: Window, buffer):
    match key:
        case "q":
            exit(0)
        case "KEY_UP":
            cursor.move_up(buffer)
            window.up(cursor)
            window.horizontal_scroll(cursor)
        case "KEY_DOWN":
            cursor.move_down(buffer)
            window.down(cursor, buffer)
            window.horizontal_scroll(cursor)
        case "KEY_LEFT":
            left(cursor, window, buffer)
        case "KEY_RIGHT":
            right(cursor, window, buffer)
        case "\n":
            buffer.line_break(cursor)
            right(cursor, window, buffer)
        case ["KEY_DELETE" | "KEY_BACKSPACE" | "\b" | "\x7f"]:
            if (cursor.row, cursor.col) > (0, 0):
                left(cursor, window, buffer)
                buffer.delete(cursor)
        case '\x1b':
            buffer.save()
            exit(0)
        case other:
            if ord(other) == 127:
                if (cursor.row, cursor.col) > (0, 0):
                    left(cursor, window, buffer)
                    buffer.delete(cursor)

            buffer.write(cursor, other)
            for _ in other:
                right(cursor, window, buffer)


if __name__ == "__main__":
    curses.wrapper(editor)
