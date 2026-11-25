# Changelog

## [1.0.3-dev] - Unreleased
- Preserve queued tasks on restart.
- Save exact final MKV size in bytes, with displayed MB derived from the file.
- Development only; stable release is unchanged.



## [1.0.2] - 2026-11-24

### Reliability
- Improve monitoring of free disk space while downloading, with a critical-space safeguard.
- Smooth reported transfer speed and ETA across video and audio downloads.
- Keep aggregate progress from moving backwards between separate streams.
- Add clearer messages for common source, format, network, storage and processing errors.

### Verification
- Add a separate read-only diagnostic script for queue, retry, timezone, chapters and subtitle fallback checks.
- End-to-end tests of restart/resume, multi-site downloads, comments, subtitles and scheduled execution remain open in GitHub Issues until verified.

## [1.0.1] - 2026-11-24
- Use the Home Assistant timezone instead of a fixed timezone.
- Expand single-video yt-dlp site support, chapter handling, comment controls and subtitle fallback.

## [1.0.0] - 2026-11-22
- Initial public release.
