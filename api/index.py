import json
import os
import re
import time

import requests
from flask import Flask, jsonify, request
from mcstatus import JavaServer

app = Flask(__name__)

# =============== MCStatus ===============

session = requests.Session()
DEFAULT_TIMEOUT = 3


def sanitize_url(url):
    return re.sub(r"^https?://", "", url).split("/")[0]


def handle_mcapi_response(data):
    if "status" not in data:
        return jsonify({"error": "No status field in response"}), 500
    if data["status"] == "success":
        return jsonify(data), 200
    if data["status"] == "error":
        return jsonify({"error": data["status"]}), 500
    return jsonify({"error": "Unknown status code"}), 404


def handle_mcapi_v2_response(data):
    try:
        duration_ns = int(data.get("duration", 0))
        time.sleep(duration_ns / 1_000_000_000)
    except (ValueError, TypeError):
        pass
    return handle_mcapi_response(data)


def fetch_json(url):
    try:
        resp = session.get(url, timeout=DEFAULT_TIMEOUT)
        return resp.json()
    except Exception as e:
        return {"_error": str(e)}


@app.route("/mcstatus/v1/<path:raw_url>")
def check_status_v1(raw_url):
    sanitized = sanitize_url(raw_url)
    data = fetch_json(f"https://mcapi.us/server/status?ip={sanitized}")
    if "_error" in data:
        return jsonify({"error": data["_error"]}), 500
    return handle_mcapi_response(data)


@app.route("/mcstatus/v2/<path:raw_url>")
def check_status_v2(raw_url):
    sanitized = sanitize_url(raw_url)
    data = fetch_json(f"https://mcapi.us/server/status?ip={sanitized}")
    if "_error" in data:
        return jsonify({"error": data["_error"]}), 500
    return handle_mcapi_v2_response(data)


@app.route("/mcstatus/v2/<path:raw_url>/<path:port>")
def check_status_v2_port(raw_url, port):
    sanitized = sanitize_url(raw_url)
    data = fetch_json(f"https://mcapi.us/server/status?ip={sanitized}&port={port}")
    if "_error" in data:
        return jsonify({"error": data["_error"]}), 500
    return handle_mcapi_v2_response(data)


@app.route("/mcstatus/v3/<path:raw_url>")
def check_status_v3(raw_url):
    sanitized = sanitize_url(raw_url)
    data = fetch_json(f"https://api.mcsrvstat.us/3/{sanitized}")
    if "_error" in data:
        return jsonify({"error": data["_error"]}), 500

    if "online" not in data:
        return jsonify({"error": "No status field in response"}), 400
    if data["online"]:
        return jsonify(data), 200
    if not data["online"]:
        return jsonify({"online": False}), 503
    return jsonify({"error": "Unknown status code"}), 400


@app.route("/mcstatus/v4/<path:raw_url>")
def check_status_v4(raw_url):
    sanitized = sanitize_url(raw_url)
    data = fetch_json(f"https://mcapi.us/server/status?ip={sanitized}")
    if "_error" in data:
        return jsonify({"error": data["_error"]}), 500
    return handle_mcapi_response(data)


@app.route("/mcstatus/v5/<path:raw_url>")
def check_status_v5(raw_url):
    sanitized = sanitize_url(raw_url)

    try:
        server = JavaServer.lookup(sanitized)
        status = server.status()
        response = {
            "online": True,
            "players": {
                "online": status.players.online,
                "max": status.players.max
            },
            "version": status.version.name,
            "motd": status.description
        }
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify(response)


# =============== UNITED EMPIRES ===============

JSON_FILE = "ue-agree.json"
_last_request_time = {}
USER_ID_REGEX = r"^user_[A-Za-z0-9]{24,}$"


def is_valid_user_id(user_id: str) -> bool:
    return re.match(USER_ID_REGEX, user_id) is not None


def can_request(user_id: str) -> bool:
    now = time.time()
    last = _last_request_time.get(user_id, 0)
    if now - last < 5:  # 5-second limit
        return False
    _last_request_time[user_id] = now
    return True


def load_agreements():
    if not os.path.exists(JSON_FILE):
        with open(JSON_FILE, "w") as f:
            json.dump({}, f)
    with open(JSON_FILE, "r") as f:
        return json.load(f)


def save_agreements(data):
    with open(JSON_FILE, "w") as f:
        json.dump(data, f, indent=4)


@app.route("/ue/v1/status", methods=["GET"])
def server_status():
    request = requests.get("https://api.xdpxi.dev/mcstatus/v5/ue.xdpxi.net")

    if request.status_code == 200:
        return request.json()

    return 'Server status unresponsive', 500


@app.route("/ue/v1/agree/<clerk_user_id>", methods=["GET"])
def agree(clerk_user_id):
    if not is_valid_user_id(clerk_user_id):
        return jsonify({"status": "error", "message": "Invalid Clerk user ID"}), 400

    if not can_request(clerk_user_id):
        return jsonify({"status": "error", "message": "Too many requests"}), 429

    if os.environ.get("VERCEL") == "1":
        try:
            response = requests.get(f"http://api.xdpxi.net:40176/ue/v1/agree/{clerk_user_id}")
            response.raise_for_status()
            return jsonify(response.json()), response.status_code
        except requests.exceptions.RequestException as e:
            return jsonify({"status": "error", "message": str(e)}), 500
    else:
        agreements = load_agreements()
        agreements[clerk_user_id] = True
        save_agreements(agreements)
        return jsonify({"status": "success", "user_id": clerk_user_id, "message": "Agreement recorded"}), 200


@app.route("/ue/v1/check/<clerk_user_id>", methods=["GET"])
def check_agreement(clerk_user_id):
    if not is_valid_user_id(clerk_user_id):
        return jsonify({"status": "error", "message": "Invalid Clerk user ID"}), 400

    if not can_request(clerk_user_id):
        return jsonify({"status": "error", "message": "Too many requests"}), 429

    if os.environ.get("VERCEL") == "1":
        try:
            response = requests.get(f"http://api.xdpxi.net:40176/ue/v1/check/{clerk_user_id}")
            response.raise_for_status()
            return jsonify(response.json()), response.status_code
        except requests.exceptions.RequestException as e:
            return jsonify({"status": "error", "message": str(e)}), 500
    else:
        agreements = load_agreements()
        agreed = agreements.get(clerk_user_id, False)
        return jsonify({"user_id": clerk_user_id, "agreed": agreed}), 200


# =============== XDPXI ===============

@app.route("/xdpxi/v1/ping", methods=["GET"])
def ping_pong():
    ip = request.headers.get("X-Forwarded-For", request.remote_addr) or "Unknown"
    return f"Pong! {ip}", 200


# =====================================

if __name__ == "__main__":
    app.run(debug=True)
