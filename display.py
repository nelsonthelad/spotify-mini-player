from machine import Pin, I2C
from ssd1306 import SSD1306_I2C

class Display:
    def __init__(self, scl, sda):
        i2c = I2C(0, scl=Pin(scl), sda=Pin(sda))
        self.oled = SSD1306_I2C(128, 64, i2c)

    def draw_music_icon(self, x, y):
        note = [
            0b0001100,
            0b0001110,
            0b0001011,
            0b0001001,
            0b0111000,
            0b1111000,
            0b0110000
        ]
        for i, row in enumerate(note):
            for j in range(7):
                if (row >> (6 - j)) & 1:
                    self.oled.pixel(x + j, y + i, 1)

    def draw_person_icon(self, x, y):
        icon = [
            0b0011100,
            0b0111110,
            0b1101011,
            0b1101011,
            0b0111110,
            0b0011100,
            0b1111111
        ]
        for i, row in enumerate(icon):
            for j in range(7):
                if (row >> (6 - j)) & 1:
                    self.oled.pixel(x + j, y + i, 1)

    def draw_play_icon(self, x, y):
        icon = [
            0b1100000,
            0b1111000,
            0b1111110,
            0b1111111,
            0b1111110,
            0b1111000,
            0b1100000
        ]
        for i, row in enumerate(icon):
            for j in range(7):
                if (row >> (6 - j)) & 1:
                    self.oled.pixel(x + j, y + i, 1)

    def display_song(self, song, artist, progress_ms, duration_ms, is_playing):
        self.oled.fill(0)

        # Song name
        self.draw_music_icon(0, 0)
        self.oled.text(song[:18], 10, 0)

        # Artist name
        self.draw_person_icon(0, 18)
        self.oled.text(artist[:18], 10, 18)

        # Progress bar
        bar_x = 0
        bar_y = 39
        bar_width = 128
        bar_height = 6
        self.oled.fill_rect(bar_x, bar_y, bar_width, bar_height, 0)
        self.oled.rect(bar_x, bar_y, bar_width, bar_height, 1)

        # Fill progress
        if duration_ms > 0:
            progress_ratio = progress_ms / duration_ms
            progress_pixels = int(progress_ratio * (bar_width - 2))
            self.oled.fill_rect(bar_x + 1, bar_y + 1, progress_pixels, bar_height - 2, 1)

        # Time display
        current_s = int(progress_ms / 1000)
        total_s = int(duration_ms / 1000)
        current_m, current_s = divmod(current_s, 60)
        total_m, total_s = divmod(total_s, 60)
        time_text = f"{current_m}:{current_s:02d}/{total_m}:{total_s:02d}"

        # Play icon + time
        self.draw_play_icon(0, 52)
        self.oled.text(time_text, 10, 52)

        self.oled.show()

    def draw_spotify_logo(self, x, y):
        # Outer circle
        for i in range(32):
            for j in range(32):
                dx = i - 16
                dy = j - 16
                dist = (dx * dx + dy * dy) ** 0.5
                if 14.5 < dist < 16.5:
                    self.oled.pixel(x + i, y + j, 1)

        # Top arc
        for i in range(5, 27):
            j = int(10 + 3 * ((i - 16) ** 2) / 128)
            self.oled.pixel(x + i, y + j, 1)
            self.oled.pixel(x + i, y + j + 1, 1)

        # Middle arc
        for i in range(7, 25):
            j = int(15 + 2.5 * ((i - 16) ** 2) / 128)
            self.oled.pixel(x + i, y + j, 1)
            self.oled.pixel(x + i, y + j + 1, 1)

        # Bottom arc
        for i in range(9, 23):
            j = int(20 + 2 * ((i - 16) ** 2) / 128)
            self.oled.pixel(x + i, y + j, 1)
            self.oled.pixel(x + i, y + j + 1, 1)

    def boot_screen(self):
        self.draw_spotify_logo(0, 16)
        self.oled.text("Spotify", 52, 20)
        self.oled.text("Mini Player", 38, 32)
        self.oled.show()
