import socket, time

HOST = "0.0.0.0"
PORT = 9002

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((HOST, PORT))

print(f"[CLOUD] UDP listening on {HOST}:{PORT}")

while True:
    data, addr = sock.recvfrom(2048)
    msg = data.decode(errors="ignore")
    print(f"[CLOUD] {time.strftime('%H:%M:%S')} from={addr[0]} msg={msg}")