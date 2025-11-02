FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY build_graph.py .
ENV DATA_DIR=/data
VOLUME ["/data"]