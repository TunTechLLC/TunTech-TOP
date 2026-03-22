# TOP — TunTech Operations Platform CLI
# Phase 1 — Version 1.0
# Usage: python top.py <command> [arguments]

import sys


def print_usage():
    print()
    print("  TOP — TunTech Operations Platform")
    print()
    print("  Commands:")
    print("    new-engagement                    Create a new client and engagement")
    print("    detect-patterns   <engagement_id> Copy signals to clipboard for Claude")
    print("    load-patterns     <engagement_id> <file.sql> Load Claude pattern output")
    print("    log-agent-run     <engagement_id> <agent>    Log a completed agent run")
    print("    accept-agents     <engagement_id>            Accept all agent runs")
    print("    case-packet       <engagement_id>            Assemble and copy case packet")
    print("    populate-findings <engagement_id>            Interactively add OPD findings")
    print("    populate-roadmap  <engagement_id>            Interactively add roadmap items")
    print("    cross-engagement-report                      Run cross-engagement views")
    print()


def main():
    if len(sys.argv) < 2:
        print_usage()
        return

    command = sys.argv[1].lower()

    if command == "new-engagement":
        from commands.engagement import run
        run()

    elif command == "detect-patterns":
        if len(sys.argv) < 3:
            print("  Usage: python top.py detect-patterns <engagement_id>")
            return
        from commands.patterns import run_detect
        run_detect(sys.argv[2].upper())

    elif command == "load-patterns":
        if len(sys.argv) < 4:
            print("  Usage: python top.py load-patterns <engagement_id> <file.sql>")
            return
        from commands.patterns import run_load
        run_load(sys.argv[2].upper(), sys.argv[3])

    elif command == "log-agent-run":
        if len(sys.argv) < 4:
            print("  Usage: python top.py log-agent-run <engagement_id> <agent_name>")
            return
        from commands.agents import run_log
        run_log(sys.argv[2].upper(), sys.argv[3])

    elif command == "accept-agents":
        if len(sys.argv) < 3:
            print("  Usage: python top.py accept-agents <engagement_id>")
            return
        from commands.agents import run_accept
        run_accept(sys.argv[2].upper())

    elif command == "case-packet":
        if len(sys.argv) < 3:
            print("  Usage: python top.py case-packet <engagement_id>")
            return
        from commands.case_packet import run
        run(sys.argv[2].upper())

    elif command == "populate-findings":
        if len(sys.argv) < 3:
            print("  Usage: python top.py populate-findings <engagement_id>")
            return
        from commands.findings import run
        run(sys.argv[2].upper())

    elif command == "populate-roadmap":
        if len(sys.argv) < 3:
            print("  Usage: python top.py populate-roadmap <engagement_id>")
            return
        from commands.roadmap import run
        run(sys.argv[2].upper())

    elif command == "cross-engagement-report":
        from commands.reporting import run
        run()

    else:
        print(f"  Unknown command: {command}")
        print_usage()


if __name__ == "__main__":
    main()
