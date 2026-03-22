# TOP Output Formatting Helpers

from config import DOMAINS, CONFIDENCE_LEVELS, ROADMAP_PHASES, PRIORITY_LEVELS


def print_header(title):
    """Print a section header."""
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_confirmation(message):
    """Print a success confirmation."""
    print(f"  OK: {message}")


def print_error(message):
    """Print an error message."""
    print(f"  ERROR: {message}")


def prompt_choice(label, options):
    """
    Show a numbered list and return the selected value.
    Keeps prompting until a valid choice is made.
    """
    print(f"\n  {label}:")
    for i, option in enumerate(options, 1):
        print(f"    {i}. {option}")
    while True:
        raw = input("  Enter number: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1]
        print("  Invalid choice. Try again.")


def prompt_text(label, required=True):
    """Prompt for free text input. Keeps prompting if required and empty."""
    while True:
        value = input(f"  {label}: ").strip()
        if value or not required:
            return value
        print("  This field is required.")


def prompt_confirm(message):
    """Ask a yes/no question. Returns True for yes."""
    raw = input(f"  {message} (y/n): ").strip().lower()
    return raw == 'y'


def prompt_domain():
    return prompt_choice("Domain", DOMAINS)


def prompt_confidence():
    return prompt_choice("Confidence", CONFIDENCE_LEVELS)


def prompt_phase():
    return prompt_choice("Roadmap Phase", ROADMAP_PHASES)


def prompt_priority():
    return prompt_choice("Priority", PRIORITY_LEVELS)


def divider():
    print("  " + "-" * 56)