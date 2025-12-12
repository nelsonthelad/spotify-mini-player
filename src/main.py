import network
import time
import requests
from display import Display

# --- USER CONFIG ---
WIFI_SSID = ""
WIFI_PASS = ""
SPOTIFY_CLIENT_ID = ""
SPOTIFY_CLIENT_SECRET = ""
SPOTIFY_REFRESH_TOKEN = ""
# --------------------

REFRESH_INTERVAL = 5  # seconds

# OLED / UI
display = Display(1, 0)

ACCESS_TOKEN = None
TOKEN_EXPIRE_TIME = 0


# --- Tiny Base64 (no extra libs) ---
def b64encode_str(s):
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
    data = s.encode()
    out = ""
    for i in range(0, len(data), 3):
        b = data[i:i + 3]
        n = 0
        for x in b:
            n = (n << 8) + x
        pad = 3 - len(b)
        n <<= 8 * pad
        for j in range(4):
            if j > 3 - pad:
                out += "="
            else:
                out += alphabet[(n >> (18 - 6 * j)) & 0x3F]
    return out


# --- Wi-Fi ---
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Connecting to Wi-Fi...")
        wlan.connect(WIFI_SSID, WIFI_PASS)
        while not wlan.isconnected():
            time.sleep(0.25)
    print("Connected:", wlan.ifconfig())


# --- Spotify Auth ---
def refresh_spotify_token():
    global ACCESS_TOKEN, TOKEN_EXPIRE_TIME

    url = "https://accounts.spotify.com/api/token"
    auth = b64encode_str(f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}")
    headers = {
        "Authorization": "Basic " + auth,
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = "grant_type=refresh_token&refresh_token=" + SPOTIFY_REFRESH_TOKEN

    try:
        res = requests.post(url, data=data, headers=headers)
        if res.status_code == 200:
            j = res.json()
            ACCESS_TOKEN = j["access_token"]
            # cache an approximate expiry to avoid refreshing too often
            TOKEN_EXPIRE_TIME = time.time() + int(j.get("expires_in", 3600)) - 30
            print("Token refreshed")
            return True
        else:
            print("Token refresh failed:", res.status_code, res.text)
    except Exception as e:
        print("Token refresh error:", e)
    return False


# --- Spotify API ---
def get_current_song():
    """Return (song, artist, duration_ms, progress_ms, is_playing)."""
    global ACCESS_TOKEN

    # Refresh token if missing/expired
    if ACCESS_TOKEN is None or time.time() >= TOKEN_EXPIRE_TIME:
        if not refresh_spotify_token():
            return ("Network/Auth error", "", 0, 0, False)

    url = "https://api.spotify.com/v1/me/player/currently-playing"
    headers = {"Authorization": "Bearer " + ACCESS_TOKEN}

    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            data = res.json()
            item = data.get("item") or {}
            song = item.get("name", "Unknown Song")
            artist = (item.get("artists") or [{}])[0].get("name", "Unknown Artist")
            duration_ms = item.get("duration_ms", 0)
            progress_ms = data.get("progress_ms", 0)
            is_playing = data.get("is_playing", False)
            return (song, artist, duration_ms, progress_ms, is_playing)

        # 204 = nothing playing
        if res.status_code == 204:
            return ("Nothing playing", "", 0, 0, False)

        # 401 = token invalid/expired → refresh and retry
        if res.status_code == 401:
            if refresh_spotify_token():
                headers = {"Authorization": "Bearer " + ACCESS_TOKEN}
                res2 = requests.get(url, headers=headers)
                if res2.status_code == 200:
                    data = res2.json()
                    item = data.get("item") or {}
                    song = item.get("name", "Unknown Song")
                    artist = (item.get("artists") or [{}])[0].get("name", "Unknown Artist")
                    duration_ms = item.get("duration_ms", 0)
                    progress_ms = data.get("progress_ms", 0)
                    is_playing = data.get("is_playing", False)
                    return (song, artist, duration_ms, progress_ms, is_playing)
            return ("Auth error", "", 0, 0, False)

        return (f"HTTP {res.status_code}", "", 0, 0, False)

    except Exception as e:
        print("Fetch error:", e)
        return ("Network error", "", 0, 0, False)


# --- MAIN ---
def main():
    connect_wifi()
    display.boot_screen()

    # Initial token (best effort)
    refresh_spotify_token()

    while True:
        song, artist, duration_ms, progress_ms, is_playing = get_current_song()
        print("Now Playing:", song, "—", artist)

        # Update OLED
        display.display_song(song, artist, progress_ms, duration_ms, is_playing)
        time.sleep(REFRESH_INTERVAL)


# --- Run Program ---
main()

