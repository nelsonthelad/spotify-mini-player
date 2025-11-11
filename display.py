from machine import Pin, I2C
from ssd1306 import SSD1306_I2C
import time

class Display:
    def __init__(self, scl, sda):
        i2c = I2C(0, scl=Pin(scl), sda=Pin(sda))
        self.oled = SSD1306_I2C(128, 64, i2c)

        # Equalizer layout (bottom 28px of the screen)
        self.EQ_X = 0
        self.EQ_Y = 36
        self.EQ_W = 128
        self.EQ_H = 28

        # Columns: width 6, gap 4 → 12 columns across 128 px
        self.COL_W = 6
        self.COL_GAP = 4
        self.COLS = 12
        self.COL_SPAN = self.COL_W + self.COL_GAP
        self.COL_BASE_X = [
            self.EQ_X + i * self.COL_SPAN + 2  # 2px inner margin
            for i in range(self.COLS)
        ]

        # Animation state
        self.eq_heights = [1] * self.COLS
        self.eq_targets = [10] * self.COLS
        self.eq_peaks   = [0] * self.COLS  # little peak dots
        self.seed = 0xACE1
        self.frame = 0

        # Header cache so we only redraw text when needed
        self._cached_song = None
        self._cached_artist = None
        self._cached_playing = None

    # -------- Icons (7x7) --------
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

    def draw_pause_icon(self, x, y):
        # Two 2px bars with 1px gap
        for i in range(7):
            # left bar
            self.oled.pixel(x,     y + i, 1)
            self.oled.pixel(x + 1, y + i, 1)
            # right bar
            self.oled.pixel(x + 4, y + i, 1)
            self.oled.pixel(x + 5, y + i, 1)

    # -------- Header (song/artist + play/pause) --------
    def draw_header(self, song, artist, is_playing):
        if (song, artist, is_playing) == (self._cached_song, self._cached_artist, self._cached_playing):
            return  # no change — keep the animation smooth

        # Clear header area (top 36px)
        self.oled.fill_rect(0, 0, 128, 36, 0)

        # Song
        self.draw_music_icon(0, 0)
        self.oled.text(song[:18], 10, 0)

        # Artist
        self.draw_person_icon(0, 18)
        self.oled.text(artist[:18], 10, 18)

        # Play/Pause at bottom-left of header row
        if is_playing:
            self.draw_play_icon(0, 28)   # y=28 to keep within header area
        else:
            self.draw_pause_icon(0, 28)

        self._cached_song = song
        self._cached_artist = artist
        self._cached_playing = is_playing
        self.oled.show()

    # -------- Equalizer internals --------
    def _rand(self):
        """Tiny 16-bit LFSR pseudo-random (fast, no imports)."""
        # x^16 + x^14 + x^13 + x^11 + 1 taps for 0xB400
        x = self.seed
        bit = ((x >> 0) ^ (x >> 2) ^ (x >> 3) ^ (x >> 5)) & 1
        x = (x >> 1) | (bit << 15)
        self.seed = x
        return x

    def _new_target(self, playing):
        if playing:
            lo = 4
            hi = self.EQ_H - 2
        else:
            # idle gently when paused
            lo = 1
            hi = max(4, self.EQ_H // 5)
        return lo + (self._rand() % max(1, (hi - lo)))

    def _step_eq_state(self, playing):
        # Every few frames, choose a fresh target for a subset of columns
        # to create a wave-like effect without all bars changing at once.
        if self.frame % 6 == 0:
            col = (self.frame // 6) % self.COLS
            self.eq_targets[col] = self._new_target(playing)

        # Ease current heights toward targets; faster when playing.
        for i in range(self.COLS):
            cur = self.eq_heights[i]
            tgt = self.eq_targets[i]
            if playing:
                step = 2 + (i % 2)  # 2–3 px per frame
            else:
                step = 1            # slow settle when paused

            if cur < tgt:
                cur = min(cur + step, tgt)
            elif cur > tgt:
                cur = max(cur - step, tgt)
            self.eq_heights[i] = cur

            # Peak dot: decays slowly, jumps to current peak
            if cur > self.eq_peaks[i]:
                self.eq_peaks[i] = cur
            else:
                if self.frame % 3 == 0 and self.eq_peaks[i] > 0:
                    self.eq_peaks[i] -= 1

    def _draw_eq_frame(self):
        # Clear EQ area
        self.oled.fill_rect(self.EQ_X, self.EQ_Y, self.EQ_W, self.EQ_H, 0)

        baseline = self.EQ_Y + self.EQ_H - 1
        for i in range(self.COLS):
            h = self.eq_heights[i]
            x = self.COL_BASE_X[i]
            # Bar (filled rect)
            self.oled.fill_rect(x, baseline - h + 1, self.COL_W, h, 1)
            # Peak dot (1px)
            peak_y = baseline - self.eq_peaks[i]
            if self.EQ_Y <= peak_y < self.EQ_Y + self.EQ_H:
                for w in range(self.COL_W):
                    self.oled.pixel(x + w, peak_y, 1)

        self.oled.show()

    # -------- Public API --------
    def set_song_and_reset_eq(self, song, artist):
        # Re-seed animation for variety per track
        self.seed = (sum(ord(c) for c in (song + artist)) ^ 0xBEEF) & 0xFFFF
        # Randomize targets so the first frames aren’t uniform
        for i in range(self.COLS):
            self.eq_heights[i] = 1 + (self._rand() % (self.EQ_H // 2))
            self.eq_targets[i] = self._new_target(True)
            self.eq_peaks[i]   = 0

    def animate_frame(self, playing):
        self._step_eq_state(playing)
        self._draw_eq_frame()
        self.frame += 1

    def boot_screen(self):
        # Minimal boot: keep your existing Spotify logo if you like
        self.oled.fill(0)
        self.oled.text("Spotify", 40, 20)
        self.oled.text("Mini Player", 24, 34)
        self.oled.show()x