from __future__ import annotations

import socket
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


BUFFER_SIZE = 1024 * 32


@dataclass
class TcpServerConfig:
    port: int
    file_path: str
    host: str = "0.0.0.0"


@dataclass
class TcpClientConfig:
    host: str
    port: int
    destination_path: str


class TcpTransferError(RuntimeError):
    pass


def send_file(server: TcpServerConfig) -> None:
    file_path = Path(server.file_path)
    if not file_path.exists():
        raise TcpTransferError(f"File not found: {file_path}")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((server.host, server.port))
        sock.listen(1)
        print(f"Server listening on {server.host}:{server.port}")

        while True:
            client_socket, addr = sock.accept()
            with client_socket:
                print(f"Connected by {addr}")
                file_size = file_path.stat().st_size
                metadata = f"{file_path.name}:{file_size}"
                client_socket.sendall(metadata.encode())

                ack = client_socket.recv(1024).decode()
                if ack != "READY":
                    print("Client not ready. Disconnecting.")
                    continue

                with file_path.open("rb") as handle:
                    while chunk := handle.read(BUFFER_SIZE):
                        client_socket.sendall(chunk)
                print(f"File {file_path.name} sent successfully.")


def receive_file(client: TcpClientConfig) -> Path:
    destination = Path(client.destination_path)
    destination.mkdir(parents=True, exist_ok=True)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((client.host, client.port))
        metadata = sock.recv(1024).decode()
        if metadata.startswith("ERROR"):
            raise TcpTransferError(metadata)
        file_name, file_size = metadata.split(":")
        file_size = int(file_size)
        sock.sendall(b"READY")

        output_path = destination / file_name
        received = 0
        with output_path.open("wb") as handle:
            while received < file_size:
                chunk = sock.recv(BUFFER_SIZE)
                if not chunk:
                    break
                handle.write(chunk)
                received += len(chunk)
        print(f"File {file_name} received successfully.")
        return output_path
