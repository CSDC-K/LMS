# server.py

import socket
import threading
import json
import uuid
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template_string

class ServerLMS:
    def __init__(self, listen_port=5001, listen_address="0.0.0.0", license_file="licenses.json"):
        self.listen_address = listen_address
        self.listen_port = listen_port
        self.license_file = license_file
        self.clients = []
        self.logs = []
        self.load_licenses()

    def load_licenses(self):
        try:
            with open(self.license_file, "r") as f:
                self.licenses = json.load(f)
        except:
            self.licenses = {}

    def save_licenses(self):
        with open(self.license_file, "w") as f:
            json.dump(self.licenses, f, indent=4)

    def generate_license_key(self, license_type):
        prefix = {
            "product": "PRD",
            "trial": "TRL"
        }.get(license_type.lower(), "GEN")
        return f"{prefix}-{uuid.uuid4().hex[:4]}-{uuid.uuid4().hex[:4]}-{uuid.uuid4().hex[:4]}"

    def create_license(self, description, license_type, duration_days=30):
        key = self.generate_license_key(license_type)
        now = datetime.now()
        self.licenses[key] = {
            "Description": description,
            "Type": license_type,
            "start_date": now.strftime("%Y-%m-%d"),
            "end_date": (now + timedelta(days=duration_days)).strftime("%Y-%m-%d")
        }
        self.save_licenses()
        return key

    def delete_license(self, key):
        if key in self.licenses:
            del self.licenses[key]
            self.save_licenses()
            return True
        return False

    def check_license_validity(self, key):
        lic = self.licenses.get(key)
        if not lic:
            return "[INVALID] License not found"
        today = datetime.now().date()
        start = datetime.strptime(lic["start_date"], "%Y-%m-%d").date()
        end = datetime.strptime(lic["end_date"], "%Y-%m-%d").date()
        if start <= today <= end:
            return f"[VALID] {lic['Description']} | {lic['Type']} | Expires: {lic['end_date']}"
        return "[EXPIRED] License out of date"

    def log_event(self, message):
        timestamped = f"[{datetime.now().strftime('%H:%M:%S')}] {message}"
        print(timestamped)
        self.logs.append(timestamped)
        if len(self.logs) > 100:
            self.logs.pop(0)

    def get_logs(self):
        return self.logs

    def handle_client(self, client_socket, client_address):
        self.log_event(f"Client connected: {client_address}")
        self.clients.append((client_socket, client_address))
        try:
            while True:
                data = client_socket.recv(1024).decode().strip()
                if not data:
                    break
                resp = self.check_license_validity(data)
                self.log_event(f"{client_address} checked license: {data} => {resp}")
                client_socket.send(resp.encode())
        except Exception as e:
            self.log_event(f"ERROR with {client_address}: {e}")
        finally:
            client_socket.close()
            self.clients.remove((client_socket, client_address))
            self.log_event(f"Client disconnected: {client_address}")

    def start_socket(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((self.listen_address, self.listen_port))
        sock.listen(5)
        self.log_event(f"Server listening on {self.listen_address}:{self.listen_port}")
        while True:
            client_socket, client_address = sock.accept()
            threading.Thread(target=self.handle_client, args=(client_socket, client_address), daemon=True).start()

def create_web_app(server):
    app = Flask(__name__)

    HTML =  '''
<!doctype html><html><head><meta charset="utf-8"><title>License Panel</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
  body {
    background-color: #1c1c1e;
    color: white;
  }
  #main-container {
    background-color: #2c2c2e;
    padding: 2rem;
    border-radius: 10px;
  }
  h1 {
    text-align: center;
    margin-bottom: 2rem;
  }
  #logs {
    background-color: #1a1a1a;
    color: #00ff99;
    padding: 1rem;
    font-family: monospace;
    max-height: 300px;
    overflow-y: auto;
  }
</style>
</head><body class="p-4">
<div class="container" id="main-container">
  <h1>🔐 License Management Panel</h1>
  <form id="license-form">
    <div class="mb-3">
      <label class="form-label">Description</label>
      <input class="form-control" name="description" placeholder="Enter license description">
    </div>
    <div class="mb-3">
      <label class="form-label">License Type</label>
      <select class="form-select" name="type">
        <option value="product">Product</option>
        <option value="trial">Trial</option>
      </select>
    </div>
    <div class="mb-3">
      <label class="form-label">Duration (Days)</label>
      <input type="number" class="form-control" name="duration" value="30" placeholder="Duration in days">
    </div>
    <button type="button" class="btn btn-primary" onclick="createLicense()">Create License</button>
  </form>
  <hr>
  <h2>Active Licenses</h2>
  <ul id="license-list" class="list-group"></ul>
  <hr>
  <h2>Server Logs</h2>
  <div id="logs"></div>
</div>
<script>
async function refreshLicenses() {
  let res = await fetch('/api/licenses');
  let data = await res.json();
  let ul = document.getElementById('license-list');
  ul.innerHTML = '';
  for (let key in data) {
    let lic = data[key];
    let li = document.createElement('li');
    li.className = 'list-group-item bg-dark text-white';
    li.innerHTML = `<div><strong>${key}</strong><br>${lic.Description} (${lic.Type})<br>${lic.start_date} → ${lic.end_date}</div>
      <button class="btn btn-sm btn-danger float-end" onclick="deleteLicense('${key}')">Delete</button>`;
    ul.appendChild(li);
  }
}

async function refreshLogs() {
  let res = await fetch('/api/logs');
  let data = await res.json();
  let logs = document.getElementById('logs');
  logs.innerHTML = data.join('<br>');
}

async function createLicense() {
  let form = new FormData(document.getElementById('license-form'));
  await fetch('/api/license/add', {
    method: 'POST',
    body: JSON.stringify(Object.fromEntries(form)),
    headers: { 'Content-Type': 'application/json' }
  });
  refreshLicenses();
  refreshLogs();
}

async function deleteLicense(key) {
  await fetch('/api/license/delete/' + key, { method: 'DELETE' });
  refreshLicenses();
  refreshLogs();
}

window.onload = () => {
  refreshLicenses();
  refreshLogs();
  setInterval(refreshLogs, 5000);
};
</script>
</body></html>
'''

    @app.route('/')
    def index():
        return render_template_string(HTML)

    @app.route('/api/licenses', methods=['GET'])
    def api_list():
        server.load_licenses()
        return jsonify(server.licenses)

    @app.route('/api/license/add', methods=['POST'])
    def api_add():
        data = request.get_json()
        desc = data.get('description','')
        ltype = data.get('type','product')
        days = int(data.get('duration',30))
        key = server.create_license(desc, ltype, days)
        return jsonify({'key': key}), 201

    @app.route('/api/license/delete/<key>', methods=['DELETE'])
    def api_delete(key):
        ok = server.delete_license(key)
        return ('', 204) if ok else ('Not Found', 404)

    @app.route('/api/logs', methods=['GET'])
    def api_logs():
        return jsonify(server.get_logs())

    return app

def start_license_server(port=5001):
    server = ServerLMS(listen_port=port)
    threading.Thread(target=server.start_socket, daemon=True).start()
    return server

def start_license_webpanel(server, port=8000):
    app = create_web_app(server)
    app.run(port=port)
