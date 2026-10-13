import json
import re
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SOURCE_URL = "https://test.ooobs.ru/api/orders"


def normalize_phone(value):
    digits = re.sub(r"\D", "", str(value or ""))
    if len(digits) == 10:
        digits = "7" + digits
    elif len(digits) == 11 and digits[0] == "8":
        digits = "7" + digits[1:]
    if len(digits) != 11 or digits[0] != "7":
        return None
    return "+" + digits


def parse_date(value):
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except (ValueError, TypeError, OverflowError):
        return 0


def amount_key(value):
    try:
        return float(value or 0)
    except (ValueError, TypeError):
        return 0


def synchronize():
    request = urllib.request.Request(
        SOURCE_URL, headers={"User-Agent": "LeadSync/1.0"}
    )
    with urllib.request.urlopen(request, timeout=12) as response:
        orders = json.loads(response.read().decode("utf-8"))

    best = {}
    invalid_dropped = 0
    valid_count = 0

    for order in orders:
        phone = normalize_phone(order.get("phone"))
        if phone is None:
            invalid_dropped += 1
            continue

        valid_count += 1
        candidate = {
            "name": order.get("name", ""),
            "phone": phone,
            "email": order.get("email", ""),
            "amount": order.get("amount", 0),
        }
        rank = (amount_key(order.get("amount")), parse_date(order.get("created_at")))

        if phone not in best or rank > best[phone][0]:
            best[phone] = (rank, candidate)

    clients = [best[phone][1] for phone in sorted(best)]
    return {
        "clients": clients,
        "stats": {
            "received": len(orders),
            "unique": len(clients),
            "duplicates_merged": valid_count - len(clients),
            "invalid_dropped": invalid_dropped,
        },
    }


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ("/", "/health"):
            self.send_error(404)
            return

        try:
            body = json.dumps(
                synchronize(), ensure_ascii=False, separators=(",", ":")
            ).encode("utf-8")
            status = 200
        except Exception:
            body = b'{"error":"Synchronization failed"}'
            status = 502

        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print(fmt % args)


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 8001), Handler).serve_forever()
