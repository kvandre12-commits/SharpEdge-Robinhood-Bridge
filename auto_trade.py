#!/usr/bin/env python3
"""SharpEdge auto-trade runner: cockpit signal -> decision -> gated handoff.

Reads ~/SharpEdge-System/outputs/signal.json (written by make_cockpit.py),
runs the deterministic decision rule, and if a trade qualifies, builds a
risk-checked, confirm-gated trade-intent artifact. It NEVER submits.

  python3 auto_trade.py            # read live signal, decide
  python3 auto_trade.py --test     # force a tiny 1-contract path-validation draft

Final live submission still requires: operator confirm + ChatGPT Robinhood
connector (see cp_chatgpt_robinhood_delegate).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from sharpedge_robinhood_bridge.trade_intent import (  # noqa: E402
    decide,
    load_signal,
    prepare_trade,
    write_artifact,
)


def main() -> None:
    test = "--test" in sys.argv
    signal = load_signal()
    if not signal:
        print("No signal.json found. Run the cockpit first: "
              "python3 ~/SharpEdge-System/cockpit/make_cockpit.py")
        return

    print(f"signal: {signal.get('symbol')} ${signal.get('spot')} | "
          f"regime={signal.get('gamma_regime')} | vs_vwap={signal.get('vs_vwap')}% | "
          f"vol={signal.get('vol_mult')}x | setup={signal.get('setup_tag')}")

    decision = decide(signal, test=test)
    print(f"decision: {decision['action'].upper()} - {decision['reason']}")

    if decision["action"] != "trade":
        print("=> stand down. No artifact written. (This is the correct, honest default.)")
        return

    result = prepare_trade(decision["intent"], command="order_submit")
    path = write_artifact(result)
    p = result["delegation_payload"]
    print(f"=> {result['status'].upper()}")
    print(f"   order: {p['side']} {p['quantity']} {p['symbol']} "
          f"{p['order_type']} {p['limit_price'] or ''}")
    print(f"   risk ok: {result['risk']['ok']} | {result['risk'].get('notes')}")
    print(f"   {result['operator_action']}")
    print(f"   artifact: {path}")
    print("   NEXT: generate the ChatGPT handoff (cp_chatgpt_robinhood_delegate), "
          "then confirm in your ChatGPT app.")


if __name__ == "__main__":
    main()
