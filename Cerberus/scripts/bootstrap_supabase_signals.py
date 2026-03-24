#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys

import psycopg


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create strategy_signals table in Supabase Postgres.")
    parser.add_argument(
        "--db-url",
        default=os.getenv("SUPABASE_DB_URL", ""),
        help="Postgres connection URL; defaults to SUPABASE_DB_URL env.",
    )
    parser.add_argument(
        "--table",
        default=os.getenv("SUPABASE_SIGNAL_TABLE", "strategy_signals"),
        help="Target table name (default: strategy_signals).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.db_url:
        print("SUPABASE_DB_URL missing. Pass --db-url or export SUPABASE_DB_URL.", file=sys.stderr)
        return 1

    table = args.table
    index_name = f"idx_{table}_created_at"
    seq_name = f"{table}_id_seq"

    ddl = f"""
    create table if not exists public.{table} (
      id bigserial primary key,
      strategy_id text not null,
      symbol text not null,
      signal text not null,
      confidence double precision not null,
      created_at timestamptz not null default now()
    );
    create index if not exists {index_name} on public.{table} (created_at desc);
    grant all privileges on table public.{table} to service_role;
    grant usage, select on sequence public.{seq_name} to service_role;
    """

    with psycopg.connect(args.db_url, connect_timeout=10, sslmode="require") as conn:
        with conn.cursor() as cur:
            cur.execute(ddl)
        conn.commit()

    print(f"Supabase bootstrap done for table public.{table}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
