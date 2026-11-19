"""Main terminal entry point. Run python main.py --help for commands."""

import argparse
import sys
import time
from core import AlertAgent
from demo import main as run_demo


def main(argv=None):
    """Read command-line options and run the requested terminal mode."""
    argument_parser = argparse.ArgumentParser(add_help=False)
    argument_parser.add_argument("--watch", action="store_true")
    argument_parser.add_argument("--interval", type=int, default=900)
    argument_parser.add_argument("--alerts", action="store_true")
    # main.py handles monitoring options. demo.py handles prediction options.
    options, run_arguments = argument_parser.parse_known_args(argv)
    if "--help" in run_arguments or "-h" in run_arguments:
        print(
            "TERMINAL COMMANDS\n  python main.py                       Next three days (requires internet)\n  python main.py --date 2023-08-01     Another historical date\n  python main.py --live               Next three days with current data\n  python main.py --live --watch       Repeat every 15 minutes; Ctrl+C stops\n  python main.py --live --send-email  Email NEW live alerts when configured\n  python main.py --test-alert         Save a local test alert\n  python main.py --send-test-email    Send a TEST email when configured\n  python main.py --alerts             Show saved alerts\n  python train.py                    Train and compare course models\n\nOptional: --interval SECONDS with --watch (minimum 300). No webpage is started."
        )
        return
    # Listing past alerts does not need a new live prediction.
    if options.alerts:
        saved_alerts = AlertAgent().history()
        if not saved_alerts:
            print("No saved alerts.")
        for saved_alert in saved_alerts:
            print(
                f"\n{saved_alert['created_at']} | {saved_alert['title']}\n{saved_alert['body']}"
            )
            print("Email:", saved_alert.get("email", {}).get("status", "not sent"))
        return
    if options.watch and "--live" not in run_arguments:
        raise SystemExit("--watch requires --live.")
    if options.watch and any(
        (x in run_arguments for x in ("--test-alert", "--send-test-email"))
    ):
        raise SystemExit("Run test alerts separately, not repeatedly in watch mode.")
    if options.interval < 300:
        raise SystemExit(
            "Use an interval of at least 300 seconds to avoid excessive public API requests."
        )
    try:
        # Run once normally, or repeat while --watch is enabled.
        while True:
            try:
                run_demo(run_arguments)
            except Exception as error:
                if not options.watch:
                    raise
                print("Update failed:", type(error).__name__, str(error)[:180])
                print("This is not an all-clear. Retrying at the next interval.")
            if not options.watch:
                break
            print(
                f"\nNext check in {options.interval} seconds. Press Ctrl+C to stop.",
                flush=True,
            )
            time.sleep(options.interval)
    # Let the presenter stop monitoring cleanly with Ctrl+C.
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")


if __name__ == "__main__":
    main()
