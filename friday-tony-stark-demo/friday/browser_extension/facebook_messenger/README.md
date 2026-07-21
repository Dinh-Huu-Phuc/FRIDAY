# FRIDAY Facebook Messenger Bridge

1. Open `chrome://extensions` in Chrome.
2. Enable **Developer mode**.
3. Select **Load unpacked**.
4. Choose this `facebook_messenger` directory.
5. Keep FRIDAY Local Core running on `http://127.0.0.1:8001`.
6. Install the extension in the Chrome profile configured by `FRIDAY_CHROME_PROFILE_DIRECTORY`.
7. Keep that profile signed in at `messenger.com`.

The extension reads only visible conversation names, timestamps, unread markers, and message previews. It does not request cookie or browsing-history permissions and never sends messages.
