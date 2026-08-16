import socket
import struct

TARGET_IP = "YOUR_IP"
TARGET_PORT = 50006

TARGET_CODE = "YOUR_CODE"
TARGET_NETWORK_CODE = "YOUR_NET"
TARGET_LOCATION = "YOUR_LOC_CODE"

RSUDP_PORT = 8893
CHANNEL = "EHZ"
SAMPLE_COUNT = 5
SAMPLE_RATE = 100

def pad8(value):
    return value.encode("ascii")[:8].ljust(8, b"\x00")

def create_waveform_packet(timestamp, waveform):
    return struct.pack(
        "<d8s8s8s8s5i",
        timestamp,
        pad8(TARGET_CODE),
        pad8(TARGET_NETWORK_CODE),
        pad8(CHANNEL),
        pad8(TARGET_LOCATION),
        *waveform
    )

def parse_packet(data):
    text = data.decode("utf-8").strip().strip("{}")
    parts = text.split(",")

    channel = parts[0].strip().strip("'").strip('"')
    timestamp = float(parts[1].strip())
    waveform = [int(x.strip()) for x in parts[2:]]

    return channel, timestamp, waveform

def main():
    recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    recv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    recv_sock.bind(("0.0.0.0", RSUDP_PORT))

    send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    while True:
        data, addr = recv_sock.recvfrom(65535)

        try:
            channel, timestamp, waveform = parse_packet(data)
        except (ValueError, UnicodeDecodeError, IndexError):
            continue

        if channel != CHANNEL:
            continue

        for i in range(0, len(waveform), SAMPLE_COUNT):
            samples = waveform[i:i + SAMPLE_COUNT]

            if len(samples) != SAMPLE_COUNT:
                continue

            packet_timestamp = timestamp + (i / SAMPLE_RATE)

            packet = create_waveform_packet(
                packet_timestamp,
                samples
            )

            send_sock.sendto(
                packet,
                (TARGET_IP, TARGET_PORT)
            )

            print(
                packet_timestamp,
                samples,
                len(packet),
                flush=True
            )

if __name__ == "__main__":
    main()