# YTDL Manager

1. Paste a YouTube URL. Wait for metadata analysis.
2. Select video, audio and codec options. English subtitles are selected if available.
3. Review chapters from video/description. Comments are searched automatically only if neither has chapters, or on request.
4. Accept or ignore chapters. Optionally edit the timestamp and name columns.
5. Choose a directory using Browse or enter an existing path under `/media`.
6. Click Download video or choose a time and Schedule download. Tasks run sequentially.
7. Download Manager shows recent jobs, status, resume and cancel.

Jobs interrupted by recoverable errors retry after five minutes, up to three times. Not all downloads can be resumed due to expiring streaming URLs.

The app does not create a separate JPEG thumbnail. Embedded subtitles and chapters depend on availability and successful FFmpeg post-processing.

The estimated size is approximate when yt-dlp reports approximate sizes or bitrates; unavailable if the source does not provide enough metadata. Theme Auto attempts to match Home Assistant and falls back to browser preference.
