"""

Databricks Standard App - Data Generation

Generates every raw dataset that will be used to power the custom agent, genie, and any OLAP features in the app.
The data will be created as parquet files that write to a volume in the app's dedicated catalog.
Data will consist of Events, Customers, and Support Tickets. 
All data generated is realted from a SaaS company that provides a product to customers and has a support team that handles customer support tickets.



"""
import argparse
import numpy as np
import pandas as pd
import random
import os
import shutil

TODAY = pd.Timestamp.today().normalize()
SEED = 16
# Shared seeded generator for pandas sampling. Successive draws advance it, so tickets and
# events get different (but reproducible) customer sequences. Python's `random` is seeded in main().
RNG = np.random.default_rng(SEED)

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

PRIORITIES = ["low", "medium", "high", "urgent"]
FEATURES = ["reports", "dashboards", "data_export", "scheduler", "webhooks"]

# Ticket text by category: (subject, description template). Templates may use {feature},
# {code}, and {errors_clause}. A customer-impact sentence matching the priority is appended.
TICKET_TEXT = {
    "billing": [
        ("Question about my invoice", "Our latest invoice shows a different amount than we expected. Can you walk us through the charges?"),
        ("Charged for unused seats", "We were billed for more seats than we have active users. Please review our seat count and adjust the invoice."),
        ("Update billing contact", "Our finance contact has changed and invoices are going to the wrong person. How do we update the billing details?"),
    ],
    "bug": [
        ("Something is not working", "The {feature} page stopped loading correctly for several of our users.{errors_clause}"),
        ("{feature} shows wrong numbers", "Totals in {feature} do not match our source data after the last refresh.{errors_clause}"),
        ("Page crashes on save", "Saving changes in {feature} fails with an error message and the changes are lost.{errors_clause}"),
    ],
    "integration": [
        ("API returns errors", "Calls to the API are failing with HTTP {code}.{errors_clause}"),
        ("Webhook deliveries failing", "Our endpoint is no longer receiving webhook events and the delivery log shows HTTP {code}.{errors_clause}"),
        ("Sync job timing out", "Our scheduled data sync through the API is timing out partway through.{errors_clause}"),
    ],
    "access": [
        ("Cannot log in", "Several users get an authentication error when they try to sign in."),
        ("SSO login loop", "After signing in with SSO, users are redirected back to the login page."),
        ("New user cannot access workspace", "A new team member was invited but cannot see any of our workspace content."),
    ],
    "how-to": [
        ("How do I export a report?", "We need to share {feature} results with leadership. What is the best way to export them?"),
        ("Setting up scheduled emails", "Can {feature} results be emailed to our team on a schedule?"),
        ("Best practice for permissions", "What is the recommended way to manage access to {feature} for different teams?"),
    ],
}
IMPACT_TEXT = {
    "low": "No rush, whenever you have a chance.",
    "medium": "We would like to get this resolved this week.",
    "high": "This is slowing our team down significantly.",
    "urgent": "This is blocking our production workflows right now.",
}


def pick_priority(plan_tier: str, category: str, errors_before: int) -> str:
    """Priority depends on plan tier, ticket category, and preceding product errors, plus chance."""
    TIER_WEIGHTS = {                # low, medium, high, urgent
        "Basic":      [50, 35, 12, 3],
        "Pro":        [30, 40, 22, 8],
        "Enterprise": [15, 30, 35, 20],
    }
    CATEGORY_MULT = {
        "how-to":      [2.5, 1.2, 0.3, 0.1],
        "billing":     [1.5, 1.3, 0.6, 0.2],
        "access":      [0.5, 0.9, 1.5, 2.0],
        "bug":         [0.8, 1.0, 1.3, 1.2],
        "integration": [0.7, 1.0, 1.3, 1.5],
    }
    if errors_before >= 5:
        error_mult = [0.2, 0.6, 1.8, 3.0]
    elif errors_before >= 2:
        error_mult = [0.5, 0.9, 1.4, 1.6]
    else:
        error_mult = [1.0, 1.0, 1.0, 1.0]
    weights = [t * c * e for t, c, e in zip(TIER_WEIGHTS[plan_tier], CATEGORY_MULT[category], error_mult)]
    return random.choices(PRIORITIES, weights)[0]


def ticket_text(category: str, priority: str, errors_before: int) -> tuple[str, str]:
    subject, template = random.choice(TICKET_TEXT[category])
    feature = random.choice(FEATURES)
    code = random.choice([500, 502, 503, 504])
    errors_clause = (
        " We noticed a burst of errors in the hours before we opened this ticket."
        if errors_before >= 2 else ""
    )
    # Customers usually describe impact in line with the real priority, but not always.
    if random.random() < 0.75:
        impact = IMPACT_TEXT[priority]
    else:
        impact = IMPACT_TEXT[random.choice(PRIORITIES)]
    description = template.format(feature=feature, code=code, errors_clause=errors_clause) + " " + impact
    return subject.format(feature=feature.replace("_", " ").capitalize()), description


def generate_tickets(customers: pd.DataFrame):
    """Generate a DataFrame of support tickets based on the customers.

    Includes a helper column `planned_errors_before` (planned error events in the hours before the ticket),
    used by generate_events and dropped before writing.
    """
    RESPONSE_MINUTES = {"Basic": 240, "Pro": 120, "Enterprise": 30}   # typical first response
    PRIORITY_FACTOR = {"low": 1.5, "medium": 1.0, "high": 0.5, "urgent": 0.25}
    # Chance that a ticket is still open, by age in days (keeps a realistic live queue)
    OPEN_PROBABILITY = [(3, 0.8), (7, 0.6), (14, 0.35), (30, 0.1)]

    N_TICKETS = 1500

    # Draw every ticket's customer up front (weighted by seats) from a seeded generator:
    # reproducible across runs, but spread across customers rather than one fixed row.
    sampled = customers.sample(N_TICKETS, weights=customers.seats, replace=True, random_state=RNG)

    tickets = []
    for i, c in enumerate(sampled.itertuples()):
        # Uniform timestamp (second resolution) between signup and the batch date
        created = c.signup_date + pd.Timedelta(
            seconds=random.randint(0, int((TODAY - c.signup_date).total_seconds()))
        )
        category = random.choice(list(TICKET_TEXT))

        # Bug and integration tickets are usually preceded by a burst of product errors
        if category in ("bug", "integration"):
            errors_before = random.randint(2, 8) if random.random() < 0.7 else 0
        else:
            errors_before = random.randint(1, 2) if random.random() < 0.1 else 0

        priority = pick_priority(c.plan_tier, category, errors_before)
        subject, description = ticket_text(category, priority, errors_before)
        response = RESPONSE_MINUTES[c.plan_tier] * PRIORITY_FACTOR[priority] * random.uniform(0.5, 1.5)
        resolved = (created + pd.Timedelta(hours=random.uniform(2, 72) * PRIORITY_FACTOR[priority])).floor("s")

        age_days = (TODAY - created).total_seconds() / 86400
        open_p = next((p for max_age, p in OPEN_PROBABILITY if age_days < max_age), 0.0)
        is_resolved = resolved < TODAY and random.random() >= open_p

        tickets.append({
            "ticket_id": 100001 + i,
            "customer_id": c.id,
            "created_at": created,
            "resolved_at": resolved if is_resolved else pd.NaT,
            "category": category,
            "subject": subject,
            "description": description,
            "priority": priority,
            "status": "resolved" if is_resolved else "open",
            "first_response_minutes": round(response),
            "planned_errors_before": errors_before,
        })

    tickets_df = pd.DataFrame(tickets)
    return tickets_df

def generate_events(customers: pd.DataFrame, tickets_df: pd.DataFrame):
    """Generate a DataFrame of events based on the customers and tickets."""
    N_EVENTS = 20000

    EVENT_TYPES = ["login", "api_call", "feature_used", "error"]
    EVENT_WEIGHTS = [30, 45, 20, 5]

    # Bigger customers (more seats) generate more events
    sampled = customers.sample(N_EVENTS, weights=customers.seats, replace=True, random_state=RNG)

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
    # Link to tickets: each ticket's planned error burst lands 1-3 hours before it was opened
    for t in tickets_df[tickets_df.planned_errors_before > 0].itertuples():
        for _ in range(t.planned_errors_before):
            lead = pd.Timedelta(seconds=random.randint(3600, 3 * 3600))
            events.append({
                "customer_id": t.customer_id,
                "event_ts": max(t.created_at - lead, signup[t.customer_id]),
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
    write_parquet(tickets_df.drop(columns=["planned_errors_before"]), args.catalog, args.schema, "tickets", args.batch_date)
    write_parquet(events_df, args.catalog, args.schema, "events", args.batch_date)

if __name__ == "__main__":
    main()
