use redis::{aio::MultiplexedConnection, AsyncCommands};
use tracing::warn;

pub(crate) async fn connect_redis(redis_url: &str) -> Option<MultiplexedConnection> {
    if redis_url.trim().is_empty() {
        warn!("REDIS_URL empty, running without Redis publish");
        return None;
    }

    let client = match redis::Client::open(redis_url) {
        Ok(client) => client,
        Err(err) => {
            warn!("invalid redis url, continue without Redis: {err}");
            return None;
        }
    };

    match client.get_multiplexed_async_connection().await {
        Ok(conn) => Some(conn),
        Err(err) => {
            warn!("redis connection failed, continue without Redis: {err}");
            None
        }
    }
}

pub(super) async fn publish_stream_message(
    redis_conn: &mut Option<MultiplexedConnection>,
    stream_key: &str,
    payload: &str,
    max_len: usize,
) -> Result<String, ()> {
    let Some(conn) = redis_conn.as_mut() else {
        return Err(());
    };
    let mut command = redis::cmd("XADD");
    command
        .arg(stream_key)
        .arg("MAXLEN")
        .arg("~")
        .arg(max_len)
        .arg("*")
        .arg("data")
        .arg(payload);
    match command.query_async::<String>(conn).await {
        Ok(stream_id) => Ok(stream_id),
        Err(err) => {
            warn!("redis stream publish failed, disabling redis publish: {err}");
            *redis_conn = None;
            Err(())
        }
    }
}

pub(super) async fn publish_redis_message(
    redis_conn: &mut Option<MultiplexedConnection>,
    channel: String,
    payload: &str,
) -> Result<(), ()> {
    let Some(conn) = redis_conn.as_mut() else {
        return Err(());
    };
    if let Err(err) = conn.publish::<_, _, usize>(channel, payload).await {
        warn!("redis publish failed, disabling redis publish: {err}");
        *redis_conn = None;
        return Err(());
    }
    Ok(())
}
