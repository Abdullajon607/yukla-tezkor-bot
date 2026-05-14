import os

# FFmpeg Windows'da xato bermasligi uchun (Yo'lni o'zingiznikiga tekshiring)
ffmpeg_bin = r"C:\Program Files\ffmpeg\bin"
if os.path.exists(ffmpeg_bin):
    os.environ["PATH"] += os.pathsep + ffmpeg_bin