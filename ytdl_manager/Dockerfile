FROM alpine:3.24
RUN apk add --no-cache python3 py3-pip deno ffmpeg ca-certificates tzdata
RUN python3 -m venv /opt/ytdl-venv
RUN /opt/ytdl-venv/bin/pip install --no-cache-dir yt-dlp==2026.10.26 yt-dlp-ejs==0.8.0
ENV PATH="/opt/ytdl-venv/bin:/usr/bin:/bin"
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY server.py /app/server.py
COPY search_engine.py /app/search_engine.py
COPY index.html /app/index.html
COPY run.sh /run.sh
RUN chmod 755 /run.sh
CMD ["/run.sh"]
