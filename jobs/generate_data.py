"""

Databricks Standard App - Data Generation

Generates every raw dataset that will be used to power the custom agent, genie, and any OLAP features in the app.
The data will be created as parquet files that write to a volume in the app's dedicated catalog.
Data will consist of Events, Customers, and Support Tickets. 
All data generated is realted from a SaaS company that provides a product to customers and has a support team that handles customer support tickets.



"""
import argparse
import pandas as pd
import random
import os
import shutil

TODAY = pd.Timestamp.today().normalize()
SEED = 16

CUSTOMER_DATA = {
    "id": [1,2,3,4,5,6,7,8,9,10],
    "name": ["Wayne Enterprises", "Stark Industries", "Oscorp", "LexCorp", "Umbrella Corporation", "Cyberdyne Systems", "Tyrell Corporation", "InGen", "Wonka Industries", "Acme Corporation"],
    "industry": ["Technology", "Technology", "Technology", "Technology", "Pharmaceuticals", "Technology", "Technology", "Biotechnology", "Food & Beverage", "Manufacturing"],
    "plan_tier": ["Basic", "Pro", "Enterprise", "Basic", "Pro", "Enterprise", "Basic", "Pro", "Enterprise", "Basic"],
    "region": ["NA-East", "NA-West", "NA-East", "NA-East", "NA-Central", "NA-West", "EU", "APAC", "NA-East", "NA-West"],
    "seats": [750, 50, 100, 8, 75, 200, 2, 30, 500, 6],
    "mrr": [7500, 500, 1000, 80, 750, 2000, 20, 300, 5000, 60],
    "signup_date": pd.to_datetime(["2024-12-03 09:14:27", "2025-02-18 16:42:05", "2025-04-07 11:03:51", "2025-05-29 22:18:34", "2025-07-14 07:55:12", "2025-09-02 13:27:48", "2025-10-21 18:09:36", "2026-01-09 05:31:20", "2026-04-16 14:46:59", "2026-08-25 10:12:03"]),
    "account_contact": ["Bruce Wayne", "Tony Stark", "Norman Osborn", "Lex Luthor", "Albert Wesker", "Miles Dyson", "Eldon Tyrell", "John Hammond", "Willy Wonka", "Wile E. Coyote"]
}


def generate_customers():
    """Generate a DataFrame of customers."""
    return pd.DataFrame(CUSTOMER_DATA)

def generate_tickets(customers: pd.DataFrame):
    """Generate a DataFrame of support tickets based on the customers."""
    SUBJECTS = {
        "billing": "Question about my invoice",
        "bug": "Something is not working",
        "integration": "API returns errors",
        "access": "Cannot log in",
        "how-to": "How do I export a report?",
    }

    # Higher tier -> more serious tickets and faster responses
    PRIORITY_WEIGHTS = {            # low, medium, high, urgent
        "Basic":      [50, 40, 9, 1],
        "Pro":        [30, 40, 25, 5],
        "Enterprise": [10, 30, 40, 20],
    }
    RESPONSE_MINUTES = {"Basic": 240, "Pro": 120, "Enterprise": 30}   # typical first response
    PRIORITY_FACTOR = {"low": 1.5, "medium": 1.0, "high": 0.5, "urgent": 0.25}

    tickets = []
    for i in range(1000):
        c = customers.sample(1, weights=customers.seats, random_state=SEED).iloc[0]
        created = c.signup_date + pd.Timedelta(days=random.randint(0, (TODAY - c.signup_date).days))
        category = random.choice(list(SUBJECTS))
        priority = random.choices(["low", "medium", "high", "urgent"], PRIORITY_WEIGHTS[c.plan_tier])[0]
        response = RESPONSE_MINUTES[c.plan_tier] * PRIORITY_FACTOR[priority] * random.uniform(0.5, 1.5)
        resolved = (created + pd.Timedelta(hours=random.uniform(2, 72) * PRIORITY_FACTOR[priority])).floor("s")
        is_resolved = resolved < TODAY

        tickets.append({
            "ticket_id": 100001 + i,
            "customer_id": c.id,
            "created_at": created,
            "resolved_at": resolved if is_resolved else pd.NaT,
            "category": category,
            "subject": SUBJECTS[category],
            "priority": priority,
            "status": "resolved" if is_resolved else "open",
            "first_response_minutes": round(response),
        })

    tickets_df = pd.DataFrame(tickets)
    return tickets_df

def generate_events(customers: pd.DataFrame, tickets_df: pd.DataFrame):
    """Generate a DataFrame of events based on the customers and tickets."""
    N_EVENTS = 20000

    EVENT_TYPES = ["login", "api_call", "feature_used", "error"]
    EVENT_WEIGHTS = [30, 45, 20, 5]
    FEATURES = ["reports", "dashboards", "data_export", "scheduler", "webhooks"]

    # Bigger customers (more seats) generate more events
    sampled = customers.sample(N_EVENTS, weights=customers.seats, replace=True, random_state=SEED)

    events = []
    for c in sampled.itertuples():
        ts = c.signup_date + pd.Timedelta(
            days=random.randint(0, (TODAY - c.signup_date).days),
            seconds=random.randint(0, 86399),
        )
        etype = random.choices(EVENT_TYPES, EVENT_WEIGHTS)[0]
        events.append({
            "customer_id": c.id,
            "event_ts": min(ts, TODAY),
            "event_type": etype,
            "feature_name": random.choice(FEATURES) if etype == "feature_used" else None,
            "status_code": (200 if random.random() < 0.95 else 500) if etype == "api_call"
                           else 500 if etype == "error" else None,
            "latency_ms": random.randint(80, 400) if etype == "api_call" else None,
        })
    signup = customers.set_index("id").signup_date
    # Link to tickets: errors show up 1-3 hours before bug / integration tickets
    for t in tickets_df[tickets_df.category.isin(["bug", "integration"])].itertuples():
        for _ in range(3):
            events.append({
                "customer_id": t.customer_id,
                "event_ts": max(ts, signup[t.customer_id]),
                "event_type": "error",
                "feature_name": None,
                "status_code": 500,
                "latency_ms": None,
            })

    events_df = pd.DataFrame(events).sort_values("event_ts").reset_index(drop=True)
    events_df[["status_code", "latency_ms"]] = events_df[["status_code", "latency_ms"]].astype("Int64")
    events_df.insert(0, "event_id", [9000001 + i for i in range(len(events_df))])
    return events_df

def write_parquet(df, catalog, schema, volume, batch_date):
    volume_root = f"/Volumes/{catalog}/{schema}/{volume}"
    folder = f"{volume_root}/{batch_date}"
    os.makedirs(folder, exist_ok=True)
    df = df.copy()
    for col in df.select_dtypes(include=["datetime"]).columns:
        df[col] = df[col].dt.tz_localize("UTC")
    df.to_parquet(f"{folder}/part-0.parquet", index=False, coerce_timestamps="us")
    print(f"Wrote {len(df)} rows to {folder}")

    #Make sure we're not keeping the same data on different days
    for name in os.listdir(volume_root):
        if name != batch_date:
            shutil.rmtree(f"{volume_root}/{name}")
            print(f"Removed old batch {volume_root}/{name}")

def main():
    random.seed(SEED)

    parser = argparse.ArgumentParser(description="Generate raw datasets for the Databricks Standard App.")
    parser.add_argument("--catalog", required=True, help="Catalog to write data to")
    parser.add_argument("--schema", required=True, help="Schema to write data to")
    parser.add_argument("--batch-date", default=TODAY.strftime("%Y-%m-%d"), help="Batch date for the data")
    args = parser.parse_args()
    
    customers_df = generate_customers()
    tickets_df = generate_tickets(customers_df)
    events_df = generate_events(customers_df, tickets_df)

    write_parquet(customers_df, args.catalog, args.schema, "customers", args.batch_date)
    write_parquet(tickets_df, args.catalog, args.schema, "tickets", args.batch_date)
    write_parquet(events_df, args.catalog, args.schema, "events", args.batch_date)

if __name__ == "__main__":
    main()
