# Render Docker deployment from the repository root.
# Python backend lives in ./backend; the public GitHub Pages files are not part of the API image.
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app.py ./app.py
COPY backend/cms_brain.py ./cms_brain.py
# Staging-only visual preview. Never copy the production config.js into this image.
COPY index.html admin.html site-design.js hq-experience.js hq-experience.css ./preview/
RUN printf '%s\n' '/* Staging preview: same-origin API only. No secrets. */' 'window.HP_API_BASE_URL = window.location.origin;' > ./preview/config.js
EXPOSE 10000
CMD ["sh", "-c", "exec uvicorn app:app --host 0.0.0.0 --port ${PORT:-10000} --proxy-headers"]
