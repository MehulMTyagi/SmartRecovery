import base64
import hashlib
import hmac
import json
import mimetypes
import os
import secrets
import smtplib
import sys
from copy import deepcopy
from datetime import datetime
from email.message import EmailMessage
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data.json"
ENV_FILE = BASE_DIR / ".env"
UNIVERSITY_DOMAIN = "@bennett.edu.in"
ADMIN_EMAIL = "s24bcau0044@bennett.edu.in"
PICKUP_POINT = "Official Lost and Found Office, Bennett University Campus"
SESSION_COOKIE = "smartrecover_session"


def load_env():
    env = {}
    if ENV_FILE.exists():
        for raw_line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip().strip('"').strip("'")
    return env


ENV = load_env()
SMTP_EMAIL = ENV.get("SMTP_EMAIL", "smartrecoverlostandfound@gmail.com")
SMTP_PASSWORD = ENV.get("SMTP_APP_PASSWORD", "")
SMTP_HOST = ENV.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(ENV.get("SMTP_PORT", "465"))


def now_iso():
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def uid(prefix):
    return f"{prefix}-{secrets.token_hex(6)}"


def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 150000).hex()
    return f"{salt}${digest}"


def verify_password(password, stored):
    if "$" not in stored:
      return False
    salt, expected = stored.split("$", 1)
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 150000).hex()
    return hmac.compare_digest(actual, expected)


def default_data():
    return {
        "users": [],
        "sessions": {},
        "lostItems": [],
        "foundItems": [],
        "claims": [],
        "emailLogs": [],
        "eventKeys": [],
    }


def load_data():
    if not DATA_FILE.exists():
        data = default_data()
        save_data(data)
        return data
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        data = default_data()
        save_data(data)
        return data


def save_data(data):
    DATA_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


DATA = load_data()


def is_university_email(email):
    return email.strip().lower().endswith(UNIVERSITY_DOMAIN)


def is_admin_email(email):
    return email.strip().lower() == ADMIN_EMAIL


def strip_user(user):
    clean = deepcopy(user)
    clean.pop("passwordHash", None)
    return clean


def get_user_by_id(user_id):
    return next((user for user in DATA["users"] if user["id"] == user_id), None)


def get_user_by_email(email):
    email = email.lower()
    return next((user for user in DATA["users"] if user["email"].lower() == email), None)


def get_found_item(found_item_id):
    return next((item for item in DATA["foundItems"] if item["id"] == found_item_id), None)


def approved_claim_for_item(found_item_id):
    return next(
        (claim for claim in DATA["claims"] if claim["foundItemId"] == found_item_id and claim["status"] == "approved"),
        None,
    )


def unique_words(text):
    cleaned = "".join(ch.lower() if ch.isalnum() or ch.isspace() else " " for ch in text or "")
    return sorted({word for word in cleaned.split() if len(word) > 2})


def compute_match_score(lost_item, found_item):
    lost_name = " ".join(unique_words(lost_item["itemName"]))
    found_name = " ".join(unique_words(found_item["itemName"]))
    lost_words = set(unique_words(f'{lost_item["itemName"]} {lost_item["description"]}'))
    found_words = set(unique_words(f'{found_item["itemName"]} {found_item["description"]}'))
    overlap = len(lost_words & found_words)
    name_similarity = 35 if lost_name and found_name and (lost_name in found_name or found_name in lost_name) else 0
    location_bonus = 18 if lost_item["location"].strip().lower() == found_item["location"].strip().lower() else 0
    return min(name_similarity + overlap * 12 + location_bonus, 100)


def suggested_matches_for_user(user_id):
    matches = []
    for lost_item in DATA["lostItems"]:
        if lost_item["userId"] != user_id:
            continue
        for found_item in DATA["foundItems"]:
            score = compute_match_score(lost_item, found_item)
            if score >= 24:
                matches.append({"lostItem": lost_item, "foundItem": found_item, "score": score})
    matches.sort(key=lambda item: item["score"], reverse=True)
    return matches


def claim_history_for_user(user_id):
    claims = []
    for claim in DATA["claims"]:
        if claim["userId"] == user_id:
            claims.append(claim)
            continue
        found_item = get_found_item(claim["foundItemId"])
        if found_item and found_item["userId"] == user_id:
            claims.append(claim)
    claims.sort(key=lambda item: item["createdAt"], reverse=True)
    return claims


def suspicious_activity():
    results = []
    for user in DATA["users"]:
        user_claims = [claim for claim in DATA["claims"] if claim["userId"] == user["id"]]
        rejected = sum(1 for claim in user_claims if claim["status"] == "rejected")
        unique_items = len({claim["foundItemId"] for claim in user_claims})
        flags = []
        if len(user_claims) >= 4:
            flags.append("High claim volume")
        if rejected >= 2:
            flags.append("Repeated rejected claims")
        if len(user_claims) > unique_items + 2:
            flags.append("Multiple duplicate attempts")
        if flags:
            results.append({"user": strip_user(user), "flags": flags})
    return results


def create_pickup_token():
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "SR-" + "".join(secrets.choice(alphabet) for _ in range(6))


def send_email_if_configured(to_email, subject, body):
    sent = False
    error = ""
    if SMTP_PASSWORD:
        message = EmailMessage()
        message["From"] = SMTP_EMAIL
        message["To"] = to_email
        message["Subject"] = subject
        message.set_content(body)
        try:
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
                server.login(SMTP_EMAIL, SMTP_PASSWORD)
                server.send_message(message)
            sent = True
        except Exception as exc:
            error = str(exc)
    else:
        error = "SMTP_APP_PASSWORD not configured"
    return sent, error


def log_and_send_email(user_id, subject, body, email_type, event_key):
    user = get_user_by_id(user_id)
    if not user or is_admin_email(user["email"]) or event_key in DATA["eventKeys"]:
        return
    sent, error = send_email_if_configured(user["email"], subject, body)
    DATA["eventKeys"].append(event_key)
    DATA["emailLogs"].insert(
        0,
        {
            "id": uid("email"),
            "to": user["email"],
            "subject": subject,
            "body": body,
            "type": email_type,
            "createdAt": now_iso(),
            "deliveryStatus": "sent" if sent else "queued",
            "deliveryError": error,
        },
    )


def notify_on_match(lost_item, found_item, score):
    lost_owner = get_user_by_id(lost_item["userId"])
    found_reporter = get_user_by_id(found_item["userId"])
    body = (
        "Smart Recover found a possible match.\n\n"
        f'Lost item: {lost_item["itemName"]}\n'
        f'Found item: {found_item["itemName"]}\n'
        f"Match score: {score}%\n"
        f'Lost location: {lost_item["location"]}\n'
        f'Found location: {found_item["location"]}\n\n'
        "Open Smart Recover to review the suggested match and proceed with verification if it looks correct."
    )
    if lost_owner:
        log_and_send_email(
            lost_owner["id"],
            f'Possible match found for {lost_item["itemName"]}',
            body,
            "match",
            f'match:{lost_item["id"]}:{found_item["id"]}:lost:{lost_owner["id"]}',
        )
    if found_reporter and (not lost_owner or found_reporter["id"] != lost_owner["id"]):
        founder_body = (
            "A user may be looking for the item you submitted.\n\n"
            f'Found item: {found_item["itemName"]}\n'
            f'Possible lost report: {lost_item["itemName"]}\n'
            f"Match score: {score}%\n\n"
            f"If a claim is approved, Smart Recover will route collection through {PICKUP_POINT}."
        )
        log_and_send_email(
            found_reporter["id"],
            "Your found item may match a lost report",
            founder_body,
            "match",
            f'match:{lost_item["id"]}:{found_item["id"]}:found:{found_reporter["id"]}',
        )


def process_matches_for_lost_item(lost_item):
    for found_item in DATA["foundItems"]:
        score = compute_match_score(lost_item, found_item)
        if score >= 24:
            notify_on_match(lost_item, found_item, score)


def process_matches_for_found_item(found_item):
    for lost_item in DATA["lostItems"]:
        score = compute_match_score(lost_item, found_item)
        if score >= 24:
            notify_on_match(lost_item, found_item, score)


def public_state_for(user):
    user_id = user["id"]
    has_lost_access = is_admin_email(user["email"]) or any(item["userId"] == user_id for item in DATA["lostItems"])
    discoverable_found_items = (
        DATA["foundItems"]
        if has_lost_access
        else [item for item in DATA["foundItems"] if item["userId"] == user_id]
    )
    return {
        "currentUser": strip_user(user),
        "users": [strip_user(entry) for entry in DATA["users"]],
        "lostItems": DATA["lostItems"],
        "foundItems": DATA["foundItems"],
        "discoverableFoundItems": discoverable_found_items,
        "claims": claim_history_for_user(user_id),
        "allClaims": DATA["claims"] if is_admin_email(user["email"]) else [],
        "emailLogs": [email for email in DATA["emailLogs"] if email["to"].lower() == user["email"].lower()],
        "matches": suggested_matches_for_user(user_id),
        "suspicious": suspicious_activity() if is_admin_email(user["email"]) else [],
        "pendingClaims": [claim for claim in DATA["claims"] if claim["status"] == "pending"] if is_admin_email(user["email"]) else [],
        "config": {
            "universityDomain": UNIVERSITY_DOMAIN,
            "adminEmail": ADMIN_EMAIL,
            "pickupPoint": PICKUP_POINT,
            "smtpEmail": SMTP_EMAIL,
            "emailConfigured": bool(SMTP_PASSWORD),
        },
    }


def parse_json(handler):
    length = int(handler.headers.get("Content-Length", "0"))
    raw = handler.rfile.read(length) if length else b"{}"
    if not raw:
        return {}
    return json.loads(raw.decode("utf-8"))


class SmartRecoverHandler(BaseHTTPRequestHandler):
    server_version = "SmartRecover/1.0"

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            return self.send_json({"ok": True})
        if parsed.path == "/api/state":
            user = self.require_user()
            if not user:
                return
            return self.send_json(public_state_for(user))
        return self.serve_static(parsed.path)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/signup":
            return self.handle_signup()
        if parsed.path == "/api/login":
            return self.handle_login()
        if parsed.path == "/api/logout":
            return self.handle_logout()
        if parsed.path == "/api/lost-items":
            return self.handle_create_item("lost")
        if parsed.path == "/api/found-items":
            return self.handle_create_item("found")
        if parsed.path == "/api/claims":
            return self.handle_create_claim()
        if parsed.path == "/api/demo":
            return self.handle_demo()
        if parsed.path.startswith("/api/items/"):
            parts = parsed.path.strip("/").split("/")
            if len(parts) == 5 and parts[4] == "delete":
                return self.handle_delete_item(parts[2], parts[3])
        if parsed.path.startswith("/api/claims/"):
            parts = parsed.path.strip("/").split("/")
            if len(parts) == 4:
                claim_id = parts[2]
                action = parts[3]
                return self.handle_claim_action(claim_id, action)
        self.send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

    def current_user(self):
        cookie = SimpleCookie(self.headers.get("Cookie"))
        session_token = cookie.get(SESSION_COOKIE)
        if not session_token:
            return None
        user_id = DATA["sessions"].get(session_token.value)
        if not user_id:
            return None
        return get_user_by_id(user_id)

    def require_user(self):
        user = self.current_user()
        if not user:
            self.send_json({"error": "Authentication required"}, status=HTTPStatus.UNAUTHORIZED)
            return None
        return user

    def require_admin(self):
        user = self.require_user()
        if not user:
            return None
        if not is_admin_email(user["email"]):
            self.send_json({"error": "Admin access required"}, status=HTTPStatus.FORBIDDEN)
            return None
        return user

    def handle_signup(self):
        payload = parse_json(self)
        email = payload.get("email", "").strip().lower()
        password = payload.get("password", "")
        if not is_university_email(email):
            return self.send_json({"error": f"Use a {UNIVERSITY_DOMAIN} email address."}, status=HTTPStatus.BAD_REQUEST)
        if get_user_by_email(email):
            return self.send_json({"error": "This email is already registered."}, status=HTTPStatus.CONFLICT)
        user = {
            "id": uid("user"),
            "name": payload.get("name", "").strip(),
            "email": email,
            "universityId": payload.get("universityId", "").strip(),
            "passwordHash": hash_password(password),
            "createdAt": now_iso(),
        }
        DATA["users"].append(user)
        session_token = secrets.token_urlsafe(32)
        DATA["sessions"][session_token] = user["id"]
        save_data(DATA)
        self.send_json(public_state_for(user), cookies={SESSION_COOKIE: session_token}, status=HTTPStatus.CREATED)

    def handle_login(self):
        payload = parse_json(self)
        email = payload.get("email", "").strip().lower()
        password = payload.get("password", "")
        user = get_user_by_email(email)
        if not user or not verify_password(password, user["passwordHash"]):
            return self.send_json({"error": "Invalid email or password."}, status=HTTPStatus.UNAUTHORIZED)
        session_token = secrets.token_urlsafe(32)
        DATA["sessions"][session_token] = user["id"]
        save_data(DATA)
        self.send_json(public_state_for(user), cookies={SESSION_COOKIE: session_token})

    def handle_logout(self):
        user = self.current_user()
        cookie = SimpleCookie(self.headers.get("Cookie"))
        session_token = cookie.get(SESSION_COOKIE)
        if session_token:
            DATA["sessions"].pop(session_token.value, None)
            save_data(DATA)
        self.send_json({"ok": True}, clear_cookie=True, status=HTTPStatus.OK if user else HTTPStatus.UNAUTHORIZED)

    def handle_create_item(self, item_type):
        user = self.require_user()
        if not user:
            return
        payload = parse_json(self)
        item = {
            "id": uid(item_type),
            "userId": user["id"],
            "itemName": payload.get("itemName", "").strip(),
            "description": payload.get("description", "").strip(),
            "location": payload.get("location", "").strip(),
            "dateTime": payload.get("dateTime", ""),
            "imageData": payload.get("imageData", ""),
            "createdAt": now_iso(),
            "status": "pending",
        }
        key = "lostItems" if item_type == "lost" else "foundItems"
        DATA[key].insert(0, item)
        if item_type == "lost":
            log_and_send_email(
                user["id"],
                f'Lost item request created for {item["itemName"]}',
                (
                    "Your lost-item request has been recorded in Smart Recover.\n\n"
                    f'Item: {item["itemName"]}\n'
                    f'Location: {item["location"]}\n'
                    f'Date/time: {item["dateTime"]}\n\n'
                    "You can now access the found-items list and review suggested matches."
                ),
                "lost-request",
                f'lost-request:{item["id"]}:{user["id"]}',
            )
            process_matches_for_lost_item(item)
        else:
            log_and_send_email(
                user["id"],
                f'Found item report created for {item["itemName"]}',
                (
                    "Your found-item report has been recorded in Smart Recover.\n\n"
                    f'Item: {item["itemName"]}\n'
                    f'Location: {item["location"]}\n'
                    f'Date/time: {item["dateTime"]}\n\n'
                    f"If a claim is approved, the item should be handed to {PICKUP_POINT}."
                ),
                "found-request",
                f'found-request:{item["id"]}:{user["id"]}',
            )
            process_matches_for_found_item(item)
        save_data(DATA)
        self.send_json(public_state_for(user), status=HTTPStatus.CREATED)

    def handle_create_claim(self):
        user = self.require_user()
        if not user:
            return
        payload = parse_json(self)
        found_item_id = payload.get("foundItemId", "")
        proof = payload.get("proof", "").strip()
        found_item = get_found_item(found_item_id)
        if not found_item:
            return self.send_json({"error": "Found item not found."}, status=HTTPStatus.NOT_FOUND)
        if approved_claim_for_item(found_item_id):
            return self.send_json({"error": "This item already has an approved claim."}, status=HTTPStatus.CONFLICT)
        for claim in DATA["claims"]:
            if claim["userId"] == user["id"] and claim["foundItemId"] == found_item_id:
                return self.send_json({"error": "You already filed a claim for this item."}, status=HTTPStatus.CONFLICT)
        claim = {
            "id": uid("claim"),
            "userId": user["id"],
            "foundItemId": found_item_id,
            "proof": proof,
            "status": "pending",
            "createdAt": now_iso(),
            "adminNotes": "",
            "pickupToken": "",
            "pickupPoint": PICKUP_POINT,
            "handoverStatus": "awaiting_admin_review",
            "handoverStatusLabel": "Awaiting admin review",
            "founderDroppedAt": "",
            "collectedAt": "",
        }
        DATA["claims"].insert(0, claim)
        save_data(DATA)
        self.send_json(public_state_for(user), status=HTTPStatus.CREATED)

    def handle_delete_item(self, item_type, item_id):
        user = self.require_user()
        if not user:
            return

        collection_key = "lostItems" if item_type == "lost" else "foundItems" if item_type == "found" else None
        if not collection_key:
            return self.send_json({"error": "Unsupported item type."}, status=HTTPStatus.BAD_REQUEST)

        item = next((entry for entry in DATA[collection_key] if entry["id"] == item_id), None)
        if not item:
            return self.send_json({"error": "Item not found."}, status=HTTPStatus.NOT_FOUND)

        if item["userId"] != user["id"] and not is_admin_email(user["email"]):
            return self.send_json({"error": "You can delete only your own items."}, status=HTTPStatus.FORBIDDEN)

        DATA[collection_key] = [entry for entry in DATA[collection_key] if entry["id"] != item_id]
        if item_type == "found":
            DATA["claims"] = [claim for claim in DATA["claims"] if claim["foundItemId"] != item_id]
        else:
            DATA["eventKeys"] = [
                key
                for key in DATA["eventKeys"]
                if not key.startswith(f"match:{item_id}:") and not key.startswith(f"lost-request:{item_id}:")
            ]

        save_data(DATA)
        self.send_json(public_state_for(user))

    def handle_claim_action(self, claim_id, action):
        user = self.require_user()
        if not user:
            return
        claim = next((entry for entry in DATA["claims"] if entry["id"] == claim_id), None)
        if not claim:
            return self.send_json({"error": "Claim not found."}, status=HTTPStatus.NOT_FOUND)
        found_item = get_found_item(claim["foundItemId"])
        founder = get_user_by_id(found_item["userId"]) if found_item else None

        if action in {"approve", "reject"}:
            if not is_admin_email(user["email"]):
                return self.send_json({"error": "Admin access required"}, status=HTTPStatus.FORBIDDEN)
            if action == "approve":
                claim["status"] = "approved"
                claim["adminNotes"] = "Ownership verified by admin review."
                claim["pickupToken"] = create_pickup_token()
                claim["pickupPoint"] = PICKUP_POINT
                claim["handoverStatus"] = "awaiting_founder_dropoff"
                claim["handoverStatusLabel"] = "Waiting for founder to deposit item at office"
                if found_item:
                    found_item["status"] = "approved"
                log_and_send_email(
                    claim["userId"],
                    f'Claim approved for {found_item["itemName"] if found_item else "your item"}',
                    (
                        "Your claim has been approved by Smart Recover admin.\n\n"
                        f'Item: {found_item["itemName"] if found_item else "Claimed item"}\n'
                        f"Pickup point: {PICKUP_POINT}\n"
                        f'Pickup token: {claim["pickupToken"]}\n\n'
                        "Please wait until the founder deposits the item at the office. You will receive another update when it is ready for pickup."
                    ),
                    "claim-approved",
                    f'claim-approved:{claim["id"]}:{claim["userId"]}',
                )
                if founder:
                    log_and_send_email(
                        founder["id"],
                        f'Admin approved a claim for {found_item["itemName"] if found_item else "your found item"}',
                        (
                            "A claim against your found item has been approved.\n\n"
                            f'Item: {found_item["itemName"] if found_item else "Found item"}\n'
                            f"Action needed: Please deposit the item at {PICKUP_POINT}.\n\n"
                            "After drop-off, update the handover status in Smart Recover so the claimant can collect it."
                        ),
                        "claim-approved",
                        f'claim-approved-founder:{claim["id"]}:{founder["id"]}',
                    )
            else:
                claim["status"] = "rejected"
                claim["adminNotes"] = "Proof did not sufficiently establish ownership."
                claim["handoverStatus"] = "rejected"
                claim["handoverStatusLabel"] = "Claim rejected"
                log_and_send_email(
                    claim["userId"],
                    f'Claim rejected for {found_item["itemName"] if found_item else "your item"}',
                    (
                        "Your claim has been rejected by Smart Recover admin.\n\n"
                        f'Item: {found_item["itemName"] if found_item else "Claimed item"}\n'
                        f'Reason: {claim["adminNotes"]}\n\n'
                        "You may submit a stronger proof if you believe this item is yours."
                    ),
                    "claim-rejected",
                    f'claim-rejected:{claim["id"]}:{claim["userId"]}',
                )
        elif action == "dropoff":
            if not founder or founder["id"] != user["id"]:
                return self.send_json({"error": "Only the founder can mark office drop-off."}, status=HTTPStatus.FORBIDDEN)
            claim["handoverStatus"] = "ready_for_pickup"
            claim["handoverStatusLabel"] = "Ready for pickup from office"
            claim["founderDroppedAt"] = now_iso()
            log_and_send_email(
                claim["userId"],
                "Your item is ready for pickup",
                (
                    f"The founder has deposited the item at {PICKUP_POINT}.\n\n"
                    f'Item: {found_item["itemName"] if found_item else "Claimed item"}\n'
                    f'Pickup token: {claim["pickupToken"]}\n\n'
                    "Bring your Bennett ID and pickup token when collecting the item."
                ),
                "pickup-ready",
                f'pickup-ready:{claim["id"]}:{claim["userId"]}',
            )
        elif action == "collect":
            if claim["userId"] != user["id"]:
                return self.send_json({"error": "Only the claimant can mark collection."}, status=HTTPStatus.FORBIDDEN)
            claim["handoverStatus"] = "collected"
            claim["handoverStatusLabel"] = "Collected by claimant"
            claim["collectedAt"] = now_iso()
            if found_item:
                found_item["status"] = "collected"
            log_and_send_email(
                claim["userId"],
                f'Collection confirmed for {found_item["itemName"] if found_item else "your item"}',
                (
                    f"Smart Recover marked your item as collected from {PICKUP_POINT}.\n\n"
                    f'Item: {found_item["itemName"] if found_item else "Claimed item"}\n'
                    f'Collected at: {claim["collectedAt"]}'
                ),
                "collected",
                f'collected-claimant:{claim["id"]}:{claim["userId"]}',
            )
            if founder:
                log_and_send_email(
                    founder["id"],
                    "Item collected from lost and found office",
                    (
                        "The claimant has collected the item you submitted.\n\n"
                        f'Item: {found_item["itemName"] if found_item else "Found item"}\n'
                        f'Collected at: {claim["collectedAt"]}'
                    ),
                    "collected",
                    f'collected-founder:{claim["id"]}:{founder["id"]}',
                )
        else:
            return self.send_json({"error": "Unsupported action."}, status=HTTPStatus.BAD_REQUEST)

        save_data(DATA)
        refresh_user = get_user_by_id(user["id"])
        self.send_json(public_state_for(refresh_user))

    def handle_demo(self):
        user = self.require_user()
        if not user:
            return
        already_seeded = any(item.get("seeded") for item in DATA["lostItems"] + DATA["foundItems"])
        if not already_seeded:
            lost_item = {
                "id": uid("lost"),
                "userId": user["id"],
                "itemName": "Blue water bottle",
                "description": "Steel bottle with a university robotics sticker and dent near the cap.",
                "location": "Central library",
                "dateTime": now_iso(),
                "imageData": "",
                "createdAt": now_iso(),
                "status": "pending",
                "seeded": True,
            }
            found_one = {
                "id": uid("found"),
                "userId": user["id"],
                "itemName": "Blue bottle",
                "description": "Metal water bottle with sticker marks, found near the library entrance.",
                "location": "Central library",
                "dateTime": now_iso(),
                "imageData": "",
                "createdAt": now_iso(),
                "status": "pending",
                "seeded": True,
            }
            found_two = {
                "id": uid("found"),
                "userId": user["id"],
                "itemName": "Black calculator",
                "description": "Scientific calculator discovered in Lecture Hall B.",
                "location": "Lecture Hall B",
                "dateTime": now_iso(),
                "imageData": "",
                "createdAt": now_iso(),
                "status": "pending",
                "seeded": True,
            }
            DATA["lostItems"].append(lost_item)
            DATA["foundItems"].extend([found_one, found_two])
            process_matches_for_lost_item(lost_item)
            save_data(DATA)
        self.send_json(public_state_for(user))

    def serve_static(self, path):
        if path in {"/", ""}:
            file_path = BASE_DIR / "index.html"
        else:
            file_path = (BASE_DIR / path.lstrip("/")).resolve()
            if BASE_DIR not in file_path.parents and file_path != BASE_DIR:
                return self.send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)
        if not file_path.exists() or not file_path.is_file():
            return self.send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)
        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        content = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def send_json(self, payload, status=HTTPStatus.OK, cookies=None, clear_cookie=False):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        if cookies:
            for key, value in cookies.items():
                self.send_header("Set-Cookie", f"{key}={value}; Path=/; HttpOnly; SameSite=Lax")
        if clear_cookie:
            self.send_header("Set-Cookie", f"{SESSION_COOKIE}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return


def main():
    port = int(os.environ.get("SMARTRECOVER_PORT", ENV.get("PORT", "8000")))
    host = os.environ.get("SMARTRECOVER_HOST", ENV.get("HOST", "0.0.0.0"))
    server = ThreadingHTTPServer((host, port), SmartRecoverHandler)
    print(f"Smart Recover running on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down Smart Recover.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
