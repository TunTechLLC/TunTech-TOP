# TOP Engagement Command
# Handles: new-engagement

from datetime import date
from db.connection import execute_query, execute_write
from utils.ids import next_client_id, next_engagement_id
from utils.formatting import (
    print_header, print_confirmation, print_error,
    prompt_text, prompt_choice, prompt_confirm, divider
)
from config import DOMAINS


def find_existing_client(firm_name):
    """Check if a client with this name already exists."""
    rows = execute_query(
        "SELECT client_id, firm_name FROM Clients WHERE LOWER(firm_name) = LOWER(?)",
        (firm_name,)
    )
    return rows[0] if rows else None


def create_client(firm_name, headcount, service_model, notes):
    """Insert a new Client record and return the new client_id."""
    client_id = next_client_id()
    today = date.today().isoformat()
    execute_write(
        """INSERT INTO Clients VALUES (?, ?, ?, ?, ?, ?)""",
        (client_id, firm_name, headcount, service_model, notes, today)
    )
    return client_id


def create_engagement(client_id, firm_name, stated_problem,
                      client_hypothesis, previously_tried, consultant_notes):
    """Insert a new Engagement record and return the new engagement_id."""
    engagement_id = next_engagement_id()
    today = date.today().isoformat()
    engagement_name = f"{firm_name} OPD {today[:7]}"
    execute_write(
        """INSERT INTO Engagements VALUES (
            ?, ?, ?, 'Active', ?, NULL, 'OPD',
            ?, ?, ?, ?, ?
        )""",
        (
            engagement_id, client_id, engagement_name, today,
            stated_problem, client_hypothesis, previously_tried,
            consultant_notes, today
        )
    )
    return engagement_id, engagement_name


def run():
    """Interactive new engagement setup."""
    print_header("NEW ENGAGEMENT SETUP")

    # Step 1 - Client name
    firm_name = prompt_text("Client firm name")

    # Step 2 - Check for existing client
    existing = find_existing_client(firm_name)
    if existing:
        print(f"\n  Found existing client: {existing['client_id']} — {existing['firm_name']}")
        use_existing = prompt_confirm("Use this existing client record?")
        if use_existing:
            client_id = existing['client_id']
            print_confirmation(f"Using existing client {client_id}")
        else:
            print_error("Cancelled. Check the firm name and try again.")
            return
    else:
        # New client - collect details
        divider()
        print("  New client — enter firm details:")
        headcount = prompt_text("Total headcount (number)")
        service_model = prompt_choice("Service model", [
            "IT Consulting — Project Delivery",
            "IT Consulting — Staff Augmentation",
            "IT Consulting — Hybrid (Project + Staff Aug)",
            "Managed Services",
            "Other"
        ])
        notes = prompt_text("Client notes (optional)", required=False)

        # Confirm before writing
        divider()
        print(f"  Firm name:     {firm_name}")
        print(f"  Headcount:     {headcount}")
        print(f"  Service model: {service_model}")
        if not prompt_confirm("Create this client record?"):
            print("  Cancelled.")
            return

        client_id = create_client(firm_name, int(headcount), service_model, notes)
        print_confirmation(f"Client created: {client_id}")

    # Step 3 - Engagement details
    divider()
    print("  Engagement details:")
    stated_problem   = prompt_text("Stated problem (what leadership told you)")
    client_hypothesis = prompt_text("Client hypothesis (what they think is causing it)")
    previously_tried  = prompt_text("Previously tried (what they have already attempted)")
    consultant_notes  = prompt_text("Consultant notes (political context, sensitivities)", required=False)

    # Confirm before writing
    divider()
    print(f"  Client:           {client_id} — {firm_name}")
    print(f"  Stated problem:   {stated_problem[:60]}...")
    if not prompt_confirm("Create this engagement record?"):
        print("  Cancelled.")
        return

    engagement_id, engagement_name = create_engagement(
        client_id, firm_name, stated_problem,
        client_hypothesis, previously_tried, consultant_notes
    )

    # Success
    divider()
    print_confirmation(f"Engagement created: {engagement_id} — {engagement_name}")
    print()
    print("  Next steps:")
    safe_name = firm_name.replace(' ', '_')
    print(f"  1. Create Google Drive folder: {safe_name}_{date.today().strftime('%Y-%m')}")
    print(f"     Copy _TEMPLATE folder and rename to match above")
    print(f"  2. Copy Run Sheet template to 01_Intake/ and rename")
    print(f"  3. Fill in Run Sheet header:")
    print(f"     Client: {firm_name}")
    print(f"     Engagement: {engagement_name}")
    print(f"     Engagement ID: {engagement_id}")
    print(f"  4. Send document request list to client")
    print()