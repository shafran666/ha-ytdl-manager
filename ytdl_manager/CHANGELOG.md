# Changelog

## [1.0.1] - 2026-11-24

### Changed
- Scheduling uses the Home Assistant timezone instead of a fixed timezone.
- Support additional yt-dlp sites for individual videos containing video and audio streams.
- Reject playlists, multi-video collections and audio-only sources.
- Close unmatched brackets in chapter names imported from video metadata, descriptions and comments.
- Rename comment search control to **Search next 100 comments**.
- Add **Search all next comments** and **Stop search** controls.
- Check available disk space before starting a download.

### Fixed
- When subtitle retrieval fails, retry the video once without subtitles, retaining selected video and audio formats.
- Show subtitle unavailability in Download Manager.

### Notes
- Search by video title is not included in this release.
- Some sites require authentication or may not expose downloadable formats.
- Retry, comments and subtitle fallback behavior depend on the source service.

## [1.0.0] - 2026-11-22

Initial public release.
