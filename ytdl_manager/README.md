# YTDL Manager

Home Assistant OS local app. Open via Settings > Apps > YTDL Manager > Open Web UI.

Features: automatic quality discovery, codecs, English subtitles, chapter review, comment setlists, scheduled queue, retries, download manager and directory browser.

The app only serves HTTP to Home Assistant Supervisor via Ingress. The download directory must be an existing directory under `/media`.

No image thumbnails are requested. Jobs and last used directory persist in `/data`.

Version 1.0.2 adds file size estimates and a theme selector. Auto theme matching is best effort in Ingress; use Dark or Light if browser settings differ from HAOS.
