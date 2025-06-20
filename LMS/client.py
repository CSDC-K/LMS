# client.py

import socket
import threading

class ClientLMS:
    def __init__(self, host_ip: str, host_port: int, info_output: bool = True, error_output: bool = True):
        self.host_ip = host_ip
        self.host_port = host_port
        self.info_output = info_output
        self.error_output = error_output
        self.conn = False
        print("LSM Client Initialized.")

    def connect_server(self):
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.host_ip, self.host_port))
        except Exception as e:
            if self.error_output:
                print(f"[ERROR] connect_server: {e}")
            self.conn = False
            return
        if self.info_output:
            print("[OK] Connected to License Server.")
        self.conn = True

    def send_msg(self, message: str, encoding: int = 8):
        try:
            self.client_socket.send(message.encode(encoding))
        except Exception as e:
            if self.error_output:
                print(f"[ERROR] send_msg: {e}")
            return
        if self.info_output:
            print(f"[OK] Message sent: {message}")

    def receive_msg(self, buffer_size: int = 1024):
        try:
            self.recv_msg = self.client_socket.recv(buffer_size)
        except Exception as e:
            if self.error_output:
                print(f"[ERROR] receive_msg: {e}")
            return
        if self.info_output:
            print(f"[OK] Received: {self.recv_msg.decode()}")

    def check_license(self, license_key: str, encoding: int = 8):
        if not self.conn:
            print("[ERROR] No connection to server.")
            return

        send_thread = threading.Thread(target=self.send_msg, args=(license_key, encoding), daemon=True)
        recv_thread = threading.Thread(target=self.receive_msg, args=(1024,), daemon=True)

        send_thread.start()
        send_thread.join()
        recv_thread.start()
        recv_thread.join()

        return self.recv_msg.decode()
