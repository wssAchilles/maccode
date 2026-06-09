from __future__ import annotations

import argparse
import csv
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path


EVENT_TYPES = ["view", "cart", "remove_from_cart", "purchase"]
CATEGORIES = [
    "electronics.smartphone",
    "electronics.audio",
    "appliances.kitchen",
    "computers.notebook",
    "apparel.shoes",
    "furniture.living_room",
]
BRANDS = ["apple", "samsung", "xiaomi", "lenovo", "nike", "bosch", ""]


def generate(path: Path, rows: int) -> None:
    random.seed(20260608)
    path.parent.mkdir(parents=True, exist_ok=True)
    start = datetime(2019, 10, 1, tzinfo=timezone.utc)

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "event_time",
                "event_type",
                "product_id",
                "category_id",
                "category_code",
                "brand",
                "price",
                "user_id",
                "user_session",
            ],
        )
        writer.writeheader()
        for i in range(rows):
            category = random.choice(CATEGORIES)
            event_type = random.choices(EVENT_TYPES, weights=[75, 12, 4, 9], k=1)[0]
            base_price = round(random.uniform(8, 1800), 2)
            price = base_price if event_type == "purchase" or random.random() > 0.02 else -base_price
            event_time = start + timedelta(minutes=random.randint(0, 60 * 24 * 30))
            writer.writerow(
                {
                    "event_time": event_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "event_type": event_type,
                    "product_id": random.randint(100000, 101000),
                    "category_id": random.randint(200000, 200200),
                    "category_code": category if random.random() > 0.03 else "",
                    "brand": random.choice(BRANDS),
                    "price": price,
                    "user_id": random.randint(500000, 510000),
                    "user_session": f"s-{random.randint(1, rows // 3 + 1)}",
                }
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate sample ecommerce behavior data.")
    parser.add_argument("--output", default="data/sample/ecommerce_events.csv")
    parser.add_argument("--rows", type=int, default=10000)
    args = parser.parse_args()
    generate(Path(args.output), args.rows)
    print(f"Generated {args.rows} rows at {args.output}")


if __name__ == "__main__":
    main()
