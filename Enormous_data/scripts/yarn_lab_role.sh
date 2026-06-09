#!/usr/bin/env sh
set -eu

export HADOOP_HOME="${HADOOP_HOME:-/opt/hadoop}"
export HADOOP_CONF_DIR="${HADOOP_CONF_DIR:-/opt/hadoop/etc/hadoop}"
export JAVA_HOME="${JAVA_HOME:-/usr/lib/jvm/java-8-openjdk-arm64}"
export PATH="$HADOOP_HOME/bin:$HADOOP_HOME/sbin:$PATH"

ROLE="${1:?role is required}"
NAMENODE_RPC="${NAMENODE_RPC:-yarn-namenode:9000}"
NAMENODE_UI="${NAMENODE_UI:-yarn-namenode:9870}"
RESOURCEMANAGER_UI="${RESOURCEMANAGER_UI:-resourcemanager:8088}"

wait_for_hdfs() {
  until hdfs dfs -ls / >/dev/null 2>&1; do
    echo "waiting for HDFS at $NAMENODE_RPC"
    sleep 3
  done
}

wait_for_yarn() {
  until yarn node -list >/dev/null 2>&1; do
    echo "waiting for YARN at $RESOURCEMANAGER_UI"
    sleep 3
  done
}

format_namenode_if_needed() {
  name_dir="${HADOOP_NAMENODE_DIR:-/hadoop/dfs/name}"
  mkdir -p "$name_dir"
  if [ ! -f "$name_dir/current/VERSION" ]; then
    hdfs namenode -format -force -nonInteractive
  fi
}

case "$ROLE" in
  namenode)
    format_namenode_if_needed
    exec hdfs namenode
    ;;
  datanode)
    sleep 5
    exec hdfs datanode
    ;;
  secondarynamenode)
    wait_for_hdfs
    exec hdfs secondarynamenode
    ;;
  resourcemanager)
    wait_for_hdfs
    exec yarn resourcemanager
    ;;
  nodemanager)
    wait_for_yarn
    exec yarn nodemanager
    ;;
  *)
    echo "unknown role: $ROLE" >&2
    exit 2
    ;;
esac
