FROM enormous_data-spark-client:latest AS python-runtime

RUN mkdir -p /tmp/python-runtime/usr/local/bin /tmp/python-runtime/usr/local/include /tmp/python-runtime/usr/local/lib \
    && cp -a /usr/local/bin/python /tmp/python-runtime/usr/local/bin/python \
    && cp -a /usr/local/bin/python3 /tmp/python-runtime/usr/local/bin/python3 \
    && cp -a /usr/local/bin/python3.11 /tmp/python-runtime/usr/local/bin/python3.11 \
    && cp -a /usr/local/include/python3.11 /tmp/python-runtime/usr/local/include/python3.11 \
    && cp -a /usr/local/lib/libpython3.11.so* /tmp/python-runtime/usr/local/lib/ \
    && cp -a /usr/local/lib/python3.11 /tmp/python-runtime/usr/local/lib/python3.11 \
    && rm -rf /tmp/python-runtime/usr/local/lib/python3.11/site-packages \
    && find /tmp/python-runtime/usr/local/lib/python3.11 -type d -name __pycache__ -prune -exec rm -rf {} +

FROM ubuntu:24.04

ENV HADOOP_HOME=/opt/hadoop \
    HADOOP_CONF_DIR=/opt/hadoop/etc/hadoop \
    YARN_CONF_DIR=/opt/hadoop/etc/hadoop \
    JAVA_HOME=/usr/lib/jvm/java-8-openjdk-arm64 \
    PYSPARK_PYTHON=/usr/local/bin/python3.11 \
    PATH=/opt/hadoop/bin:/opt/hadoop/sbin:/usr/lib/jvm/java-8-openjdk-arm64/bin:$PATH

RUN apt-get update \
    && apt-get install -y --no-install-recommends procps \
    && rm -rf /var/lib/apt/lists/*

COPY hadoop /opt/hadoop
COPY java-8-openjdk-arm64 /usr/lib/jvm/java-8-openjdk-arm64
COPY --from=python-runtime /tmp/python-runtime/usr/local /usr/local

RUN mkdir -p /hadoop/dfs/name /hadoop/dfs/data /hadoop/yarn/local /hadoop/yarn/logs /opt/hadoop/logs \
    && ln -sf /usr/local/lib/libpython3.11.so.1.0 /usr/local/lib/libpython3.11.so \
    && ldconfig \
    && /usr/local/bin/python3.11 --version \
    && chmod +x /opt/hadoop/bin/* /opt/hadoop/sbin/* || true

WORKDIR /opt/hadoop
