"""Run two consumer contracts against live local v1, breaking v2, and repaired v2 APIs."""

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from jsonschema import Draft202012Validator

SCHEMAS = {
    "finance export": {
        "type": "object",
        "required": ["id", "balance_cents"],
        "properties": {
            "id": {"type": "string"},
            "balance_cents": {"type": "integer", "minimum": 0},
        },
    },
    "operations portal": {
        "type": "object",
        "required": ["id", "stage"],
        "properties": {
            "id": {"type": "string"},
            "stage": {"enum": ["pending", "active", "closed"]},
        },
    },
}
REPLIES = {
    "v1": {"id": "acct-17", "balance_cents": 3995, "stage": "active"},
    "breaking": {
        "id": "acct-17",
        "balance": {"amount": "39.95", "currency": "USD"},
        "stage": "verified",
    },
    "compatible": {
        "id": "acct-17",
        "balance_cents": 3995,
        "balance": {"amount": "39.95", "currency": "USD"},
        "stage": "active",
        "lifecycle": "verified",
    },
}
REQUEST = {
    "type": "object",
    "required": ["account_id"],
    "additionalProperties": False,
    "properties": {"account_id": {"type": "string", "pattern": "^acct-[0-9]+$"}},
}


class Api(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/lookup":
            self.send_error(404)
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 1024:
                raise ValueError("Unsupported size")
            body = json.loads(self.rfile.read(size))
            if not Draft202012Validator(REQUEST).is_valid(body):
                raise ValueError("Unexpected request shape")
        except (ValueError, UnicodeError):
            self.send_error(422)
            return
        if body["account_id"] != "acct-17":
            self.send_error(404)
            return
        data = json.dumps(self.server.reply).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *_):
        pass


def examine(response):
    report = {}
    for name, schema in SCHEMAS.items():
        errors = list(Draft202012Validator(schema).iter_errors(response))
        report[name] = {
            "compatible": not errors,
            "violations": [
                {
                    "path": "/".join(map(str, error.path)) or "/",
                    "rule": error.validator,
                    "message": error.message,
                }
                for error in errors
            ],
        }
    return report


def run_against(version):
    with ThreadingHTTPServer(("127.0.0.1", 0), Api) as server:
        server.reply = REPLIES[version]
        thread = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{server.server_port}/lookup"
            valid = Request(
                url, data=b'{"account_id":"acct-17"}', headers={"Content-Type": "application/json"}
            )
            with urlopen(valid, timeout=4) as response:
                observed = json.load(response)
            invalid = Request(
                url, data=b'{"wrong_key":4}', headers={"Content-Type": "application/json"}
            )
            try:
                with urlopen(invalid, timeout=4) as response:
                    rejected = response.status
            except HTTPError as error:
                rejected = error.code
                error.close()
            report = examine(observed)
            return {
                "version": version,
                "accept": rejected == 422 and all(check["compatible"] for check in report.values()),
                "invalid_request_http": rejected,
                "contracts": report,
            }
        finally:
            server.shutdown()
            thread.join()


def demo():
    return {version: run_against(version) for version in REPLIES}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gate", choices=REPLIES)
    args = parser.parse_args()
    if args.gate:
        result = run_against(args.gate)
        print(json.dumps(result, indent=2))
        raise SystemExit(0 if result["accept"] else 1)
    print(json.dumps(demo(), indent=2))
