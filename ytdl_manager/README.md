# YTDL Manager

**Video download manager for Home Assistant OS**, powered by yt-dlp.

YTDL Manager provides a web interface through Home Assistant Ingress for selecting video and audio quality, managing chapters and subtitles, scheduling downloads, and monitoring a sequential download queue.

## Features

- Detect available video resolutions, audio bitrates and codecs.
- Prefer the highest available resolution, with manual selection.
- Show estimated file size when metadata is available.
- Prefer English subtitles when offered by the source.
- Detect chapters from video metadata or descriptions, and optionally search comments.
- Automatically use the highlighted chapter source, including edits to timestamps and titles.
- Embed chapters into MKV when post-processing succeeds.
- Show YouTube thumbnails in Download Manager without storing separate thumbnail files alongside videos.
- Display progress percentage, downloaded MB, speed and ETA when available.
- Filter jobs by status; reorder queued jobs; cancel, resume and delete history entries.
- Schedule downloads in Europe/Warsaw and run downloads sequentially.
- Browse folders under `/media` and remember the last directory.
- Choose Auto, Dark or Light interface theme.

## Getting started

1. Install YTDL Manager from your added app repository.
2. Set `download_directory` to an existing writable folder under `/media`.
3. Start the app and select **Open Web UI**.
4. Paste a YouTube URL and wait for metadata analysis.
5. Choose video/audio quality, codec and subtitles, and review chapters.
6. Select **Download video**, or set a time and select **Schedule download**.

## Notes

- Current public build targets AMD64 Home Assistant OS.
- Downloads depend on availability and access restrictions imposed by source services.
- The app does not require a separate JPEG thumbnail beside downloaded media.
- Errors retrieving subtitles or individual formats can still cause download failures.
- Download jobs and settings persist in the app's `/data` directory.
- This community project is not affiliated with Home Assistant or YouTube.

## Project

Maintained by [shafran666](https://github.com/shafran666).
