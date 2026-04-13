import socket, time, math
from collections import deque, defaultdict

# ===== Puertos =====
EDGE_HOST = "0.0.0.0"
EDGE_PORT = 9001

CLOUD_HOST = "127.0.0.1"  # Cloud en el mismo WSL
CLOUD_PORT = 9002

# ===== Parámetros Edge =====
WINDOW = 50
Z_THRESHOLD = 3.0
REPORT_EVERY_SEC = 2

# ===== Sockets =====
recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
recv_sock.bind((EDGE_HOST, EDGE_PORT))

send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# ===== Estado por sensor_id =====
windows = defaultdict(lambda: deque(maxlen=WINDOW))

raw_msgs = 0
raw_bytes = 0
event_msgs = 0
event_bytes = 0
t0 = time.time()

def mean_std(vals):
    n = len(vals)
    if n < 10:
        return None, None
    mu = sum(vals) / n
    var = sum((x - mu) ** 2 for x in vals) / n
    sd = math.sqrt(var) if var > 1e-12 else 1e-6
    return mu, sd

print(f"[EDGE] listening UDP on {EDGE_HOST}:{EDGE_PORT} -> cloud {CLOUD_HOST}:{CLOUD_PORT}")

while True:
    data, addr = recv_sock.recvfrom(2048)
    raw_msgs += 1
    raw_bytes += len(data)

    # Formato esperado desde ESP32:
    # sensor_id,seq,value
    msg = data.decode(errors="ignore").strip()
    parts = msg.split(",")

    if len(parts) != 3:
        continue

    sensor_id = parts[0]
    try:
        seq = int(parts[1])
        value = float(parts[2])
    except Exception:
        continue

    w = windows[sensor_id]
    w.append(value)

    mu, sd = mean_std(w)
    if mu is not None:
        z = abs((value - mu) / sd)
        if z >= Z_THRESHOLD:
            # Evento compacto a Cloud
            # ANOM,sensor_id,seq,value,z
            out = f"ANOM,{sensor_id},{seq},{value:.2f},{z:.2f}"
            payload = out.encode()
            send_sock.sendto(payload, (CLOUD_HOST, CLOUD_PORT))
            event_msgs += 1
            event_bytes += len(payload)

    # Reporte de tráfico
    if time.time() - t0 >= REPORT_EVERY_SEC:
        print(f"[EDGE] raw: {raw_msgs} msgs ({raw_bytes} B) | events: {event_msgs} msgs ({event_bytes} B)")
        t0 = time.time()
        raw_msgs = raw_bytes = event_msgs = event_bytes = 0