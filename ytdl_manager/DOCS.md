# YTDL Manager documentation

## Installation
Add `https://github.com/shafran666/ha-ytdl-manager` in **Settings > Apps > Install app > Repositories**. Install YTDL Manager, configure a writable directory under `/media`, then start the app and open its Web UI.

## Downloads
Paste a direct HTTPS URL for a single video with both video and audio streams. Playlists, multi-video collections and audio-only content are not supported. Select video/audio quality and codec, and optionally subtitles. Source support depends on yt-dlp and the remote service.

## Chapters
The app reads chapters from video metadata and descriptions. Comments are searched when neither source contains chapters, or manually using **Search next 100 comments** or **Search all next comments**. Use **Stop search** to stop further batches. The highlighted chapter source is selected automatically; edits to titles and timestamps are used when embedding chapters into MKV. Missing closing brackets in imported titles are automatically completed.

## Scheduling
Schedule times use the timezone provided by Home Assistant. The app uses this timezone to interpret and display scheduled times. Downloads run sequentially; queued jobs can be reordered.

## Download Manager
The manager displays thumbnails, progress, downloaded MB, speed and ETA when available. It supports cancellation, resuming and removing entries from the queue/history without deleting media files. If subtitles cannot be downloaded, the app makes one fallback attempt without subtitles and records the failure.

## Storage and troubleshooting
The default directory is `/media/downloads`; choose an existing writable folder under `/media`. Check the app logs for yt-dlp and FFmpeg errors. The application does not automatically switch storage when a mount is unavailable. Media sources may impose access or rate limits.
