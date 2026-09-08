# Accounting domain

This module owns the double-entry accounting ledger, chart of accounts, party and wallet accounts, vouchers, statements, escrow settlement, and vendor withdrawal workflow.

Financial writes are performed through service functions in `services_v2.py` so order and wallet operations remain atomic and idempotent.
