
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlparse
import json
import os
import psycopg2

BASE_DIR = Path(__file__).resolve().parent


class LoginHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def initialize_database(self):
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            raise RuntimeError("DATABASE_URL is not configured")

        with psycopg2.connect(database_url) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS test_submissions (
                        id BIGSERIAL PRIMARY KEY,
                        test_label TEXT NOT NULL,
                        test_phone TEXT NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                """)

    def do_POST(self):
        if urlparse(self.path).path != "/login":
            self.send_json(404, {"message": "Not found."})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 10000:
                self.send_json(400, {"message": "Invalid request size."})
                return

            data = json.loads(self.rfile.read(length))
            username = data.get("username")
            phone = data.get("phone")

            if not isinstance(username, str) or not isinstance(phone, str):
                self.send_json(400, {"message": "Invalid test data."})
                return

            username = username.strip()
            phone = phone.strip()

            if not username or not phone or len(username) > 254 or len(phone) > 30:
                self.send_json(400, {"message": "Check both fields."})
                return

            database_url = os.environ.get("DATABASE_URL")
            if not database_url:
                raise RuntimeError("DATABASE_URL is not configured")

            with psycopg2.connect(database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS test_submissions (
                            id BIGSERIAL PRIMARY KEY,
                            test_label TEXT NOT NULL,
                            test_phone TEXT NOT NULL,
                            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                        )
                    """)
                    cur.execute("""
                        INSERT INTO test_submissions (test_label, test_phone)
                        VALUES (%s, %s)
                    """, (username, phone))

            self.send_json(200, {
                "message": "Test submission saved successfully."
            })

        except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
            self.send_json(400, {"message": "Invalid request data."})
        except Exception:
            # Do not expose database credentials or internal errors to visitors.
            print("Submission failed; check server configuration and database logs.")
            self.send_json(500, {"message": "Could not save the test submission."})

    def send_json(self, status, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    handler = LoginHandler

    # Create the table before accepting requests.
    handler.initialize_database(handler.__new__(handler)) if False else None

    class ReadyHandler(handler):
        database_ready = False

        def do_GET(self):
            if self.path == "/health":
                self.send_json(200, {"status": "ok"})
                return
            super().do_GET()

    # Initialize database schema at startup.
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("Set DATABASE_URL in Render Environment first.")

    with psycopg2.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS test_submissions (
                    id BIGSERIAL PRIMARY KEY,
                    test_label TEXT NOT NULL,
                    test_phone TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)

    HTTPServer(("0.0.0.0", port), ReadyHandler).serve_forever()


