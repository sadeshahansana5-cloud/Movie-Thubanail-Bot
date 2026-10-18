FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=7860 \
    PYROGRAM_WORKDIR=/tmp/sadesha-pyrogram \
    PYROGRAM_WORKERS=32 \
    MAX_CONCURRENT_TRANSMISSIONS=4

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 user
WORKDIR /home/user/app
RUN mkdir -p /tmp/sadesha-pyrogram && chown -R user:user /tmp/sadesha-pyrogram

COPY --chown=user requirements-hf.txt ./requirements.txt
RUN pip install -r requirements.txt
COPY --chown=user app.py ./app.py
COPY --chown=user sadesha_sub_logo.png ./sadesha_sub_logo.png
COPY --chown=user sadesha_sub_logo_ai_gold.png ./sadesha_sub_logo_ai_gold.png
COPY --chown=user sadesha_sub_logo_ai_royal.png ./sadesha_sub_logo_ai_royal.png
COPY --chown=user sadesha_sub_logo_ai_neon.png ./sadesha_sub_logo_ai_neon.png
COPY --chown=user sadesha_sub_line_neon.png ./sadesha_sub_line_neon.png
COPY --chown=user sadesha_sub_line_gold.png ./sadesha_sub_line_gold.png

USER user
EXPOSE 7860
CMD ["python", "app.py"]
