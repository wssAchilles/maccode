FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    JAVA_HOME=/usr/lib/jvm/default-java \
    SPARK_HOME=/usr/local/lib/python3.11/site-packages/pyspark \
    HADOOP_CONF_DIR=/app/configs/hadoop \
    YARN_CONF_DIR=/app/configs/hadoop \
    PATH=/usr/local/lib/python3.11/site-packages/pyspark/bin:$PATH

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends openjdk-17-jre-headless procps \
    && ln -s /usr/lib/jvm/java-17-openjdk-* /usr/lib/jvm/default-java \
    && mkdir -p /opt/gurobi \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --default-timeout=300 --retries=5 -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["python", "-m", "spark_jobs.main", "--config", "configs/local.yaml"]
