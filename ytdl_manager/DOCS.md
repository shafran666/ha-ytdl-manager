# YTDL Manager documentation

## Installation

1. In Home Assistant, open **Settings > Apps > Install app > Repositories**.
2. Add `https://github.com/shafran666/ha-ytdl-manager`.
3. Install **YTDL Manager** and configure an existing writable directory under `/media`.
4. Start the app and select **Open Web UI**.

## Downloading

Paste a supported YouTube URL and wait for metadata analysis. Choose the available video quality, audio bitrate and codec. The app may show an estimated file size. The highest available video and audio qualities are selected by default.

## Subtitles

English is preferred when available. Select another language or **None**. Subtitle availability and embedding are not guaranteed; source rate limits may interrupt a download.

## Chapters

The app checks metadata and video descriptions. If neither contains chapters, it may search comments automatically; additional comment searches can be started manually. Selecting a chapter source automatically selects its timestamps and names for the download. You can edit individual rows or choose **Ignore chapters**. Successful post-processing embeds chapters into MKV.

## Download Manager

The manager offers **All**, **Downloading**, **Queued**, **Scheduled**, **Completed** and **Failed** filters. Waiting jobs can be reordered. **Cancel** stops a task, **Resume now** requeues an interrupted task, and **Delete** removes a history/queue entry without deleting the media file. Progress, downloaded MB, speed and ETA are shown when available.

## Scheduling

Times use the `Europe/Warsaw` time zone. Jobs due at the same time are processed sequentially. Interrupted downloads may be retried after five minutes, up to three attempts.

## Storage and troubleshooting

Choose an existing writable path under `/media`. The app saves job history and preferences in persistent `/data`. It does not intentionally create chapter JSON files or image sidecars beside downloads. Inspect app Logs for yt-dlp or FFmpeg errors; confirm the media mount is available before retrying.

## Appearance

Use the **Theme** selector to choose Auto, Dark or Light. Auto follows the Home Assistant theme when it can be detected, otherwise it falls back to browser preferences.
