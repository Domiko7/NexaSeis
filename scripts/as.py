import socket
import struct
import time

SOURCE_IP = "127.0.0.1"
SOURCE_PORT = 30000

TARGET_IP = "YOUR_IP"
TARGET_PORT = 50006
TARGET_NETWORK_CODE = "NET"

SAMPLE_COUNT = 5
SAMPLE_RATE = 250.0
RECONNECT_DELAY = 1.0


def pad8(value):
    return value.encode("ascii")[:8].ljust(8, b"\x00")


def get_checksum(message):
    fields = message.split(",")
    if len(fields) < 8:
        raise ValueError("message fields length is less than 8")
    checksum = 0
    for field in fields[7:-1]:
        for byte in struct.pack("<i", int(field)):
            checksum ^= byte
    return checksum


def compare_checksum(message):
    checksum_index = message.find("*")
    if checksum_index == -1:
        raise ValueError("checksum not found in message")
    received = int(message[checksum_index + 1:checksum_index + 3], 16)
    return received == get_checksum(message)


def parse_line(line):
    if not compare_checksum(line):
        raise ValueError("checksum mismatch")
    fields = line.split("*", 1)[0].rstrip(",").split(",")
    network = TARGET_NETWORK_CODE
    station = fields[2]
    location = fields[3]
    channel = fields[4]
    timestamp = int(fields[5]) / 1000.0
    sample_rate = SAMPLE_RATE
    samples = [int(value) for value in fields[7:]]
    if not channel or channel[-1] not in ("E", "N", "Z"):
        raise ValueError("unsupported channel")
    if sample_rate <= 0:
        raise ValueError("invalid sample rate")
    return network, station, location, channel, timestamp, sample_rate, samples


def create_waveform_packet(network, station, location, channel, timestamp, samples):
    return struct.pack(
        "<d8s8s8s8s5i",
        timestamp,
        pad8(station),
        pad8(network),
        pad8(channel),
        pad8(location),
        *samples,
    )


def forward_line(line, send_socket):
    network, station, location, channel, timestamp, sample_rate, samples = parse_line(line)
    for offset in range(0, len(samples), SAMPLE_COUNT):
        chunk = samples[offset:offset + SAMPLE_COUNT]
        if len(chunk) != SAMPLE_COUNT:
            continue
        packet_timestamp = timestamp + offset / sample_rate
        packet = create_waveform_packet(
            network,
            station,
            location,
            channel,
            packet_timestamp,
            chunk,
        )
        send_socket.sendto(packet, (TARGET_IP, TARGET_PORT))
        print(network, station, location, channel, packet_timestamp, chunk, flush=True)


def main():
    send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    buffer = ""
    while True:
        source_socket = None
        try:
            source_socket = socket.create_connection((SOURCE_IP, SOURCE_PORT), timeout=5.0)
            source_socket.settimeout(1.0)
            buffer = ""
            print(f"Connected to {SOURCE_IP}:{SOURCE_PORT}", flush=True)
            while True:
                try:
                    data = source_socket.recv(16384)
                except socket.timeout:
                    continue
                if not data:
                    raise ConnectionError("source connection closed")
                buffer += data.decode("utf-8", errors="ignore")
                while "\r\n" in buffer:
                    line, buffer = buffer.split("\r\n", 1)
                    if not line.strip():
                        continue
                    try:
                        forward_line(line, send_socket)
                    except (ValueError, IndexError, struct.error) as error:
                        print(f"Dropped line: {error}", flush=True)
        except (ConnectionError, OSError) as error:
            print(f"TCP error: {error}. Reconnecting...", flush=True)
            time.sleep(RECONNECT_DELAY)
        finally:
            if source_socket is not None:
                source_socket.close()


if __name__ == "__main__":
    main()
