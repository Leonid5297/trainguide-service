FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc libpq-dev fonts-dejavu-core && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Копируем шрифты DejaVu в папку сервиса для ReportLab (кириллица на Linux)
RUN cp /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf . && \
    cp /usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8004"]
