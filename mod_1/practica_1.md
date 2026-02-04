# Práctica 1 (ESP32 + WSL/Python)
**Tema:** Cómputo en el borde (Edge)  
**Arquitectura:** Sensores (ESP32) → Borde (WSL/Python) → Nube (WSL/Python)  
**Modalidad:** Individual  
**Entregable:** Reporte PDF (este documento completado + evidencias)  

---

## 1. Objetivos
1. Implementar un flujo **ESP32 (sensor) → Edge (Python) → Cloud (Python)** donde el edge procesa localmente y envía **solo eventos**.
2. Medir reducción de tráfico comparando: **datos crudos** recibidos vs **eventos** enviados.
3. Validar comunicación por UDP entre componentes.

---

## 2. Requisitos
- 1 ESP32 (Arduino IDE).
- Cable USB.
- Red WiFi 2.4 GHz.
- PC con Windows 10/11 + WSL2 (Ubuntu recomendado: 22.04+).
- Python 3 en WSL.

---

## 3. Preparación del entorno (WSL)
En Ubuntu (WSL):

```bash
sudo apt update
sudo apt install -y python3 python3-pip
python3 --version
````

Evidencia:

* Captura/copia de `python3 --version`.

---

## 4. Direccionamiento y puertos

* **Edge (Python)** escucha datos crudos en: UDP **9001**
* **Cloud (Python)** escucha eventos en: UDP **9002**
* **ESP32 Sensor** envía a: `EDGE_IP:9001`
* **Edge** envía a: `CLOUD_IP:9002`

En esta práctica, Edge y Cloud corren en el mismo PC/WSL:

* `EDGE_IP = CLOUD_IP = IP del PC en la red local` (ej. `192.168.1.50`)

---

## 5. Obtener la IP del PC (para configurar el ESP32)

En WSL:

```bash
ip a | grep inet
ip route | grep default
```

Anotar la IP local del PC (ej. `192.168.1.50`).
Evidencia:

* Copia/captura donde se vea la IP usada.

---

## 6. Parte A — Nube (Cloud): receptor de eventos (WSL/Python)

### A1. Crear carpeta de trabajo

```bash
mkdir -p edge_lab && cd edge_lab
```

### A2. Crear `cloud.py`

```bash
nano cloud.py
```

Pegar:

```python
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
```

### A3. Ejecutar Cloud

```bash
python3 cloud.py
```

Evidencia:

* Captura/copia de consola recibiendo eventos (cuando el edge esté corriendo).

---

## 7. Parte B — Borde (Edge): filtrado y detección (WSL/Python)

### B1. Crear `edge.py`

En otra terminal WSL:

```bash
cd edge_lab
nano edge.py
```

Pegar:

```python
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
```

### B2. Ejecutar Edge

```bash
python3 edge.py
```

Evidencia:

* Captura/copia donde se vea `raw` vs `events`.

---

## 8. Parte C — Sensor (ESP32): envío de datos crudos por UDP

### C1. Código Arduino (ESP32 Sensor)

> Ajustar: `WIFI_SSID`, `WIFI_PASS`, `EDGE_IP` (IP del PC), `EDGE_PORT`.
> Si no hay sensor real, se usa simulación.

Crear un sketch nuevo y pegar:

```cpp
#include <Arduino.h>
#include <WiFi.h>
#include <WiFiUdp.h>

// ===== WiFi =====
const char* WIFI_SSID = "TU_SSID";
const char* WIFI_PASS = "TU_PASSWORD";

// ===== Edge (PC/WSL) =====
IPAddress EDGE_IP(192,168,1,50); // Cambiar por IP del PC
const uint16_t EDGE_PORT = 9001;

// ===== Identidad del sensor =====
const char* SENSOR_ID = "S1";

// ===== Muestreo =====
const uint16_t SAMPLE_MS = 50;

// UDP
WiFiUDP udp;

void connectWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  Serial.print("Conectando WiFi");
  uint32_t t0 = millis();
  while (WiFi.status() != WL_CONNECTED) {
    delay(300);
    Serial.print(".");
    if (millis() - t0 > 15000) {
      Serial.println("\nReintentando WiFi...");
      WiFi.disconnect();
      WiFi.begin(WIFI_SSID, WIFI_PASS);
      t0 = millis();
    }
  }

  Serial.println("\nWiFi conectado");
  Serial.print("IP ESP32: ");
  Serial.println(WiFi.localIP());
}

float readValue() {
  uint32_t r = (uint32_t)micros();
  float noise = (float)((int)(r % 100) - 50) / 25.0f; // ~[-2,2]
  float value = 50.0f + noise;

  if ((r % 2500) < 15) value += 25.0f + (float)(r % 10);
  return value;
}

uint32_t seq = 0;
uint32_t t_last = 0;

void setup() {
  Serial.begin(115200);
  delay(200);

  connectWiFi();
  udp.begin(0);

  t_last = millis();
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
  }

  uint32_t now = millis();
  if (now - t_last >= SAMPLE_MS) {
    t_last = now;

    float v = readValue();

    // Formato crudo: sensor_id,seq,value
    char msg[64];
    snprintf(msg, sizeof(msg), "%s,%lu,%.2f", SENSOR_ID, (unsigned long)seq, v);

    udp.beginPacket(EDGE_IP, EDGE_PORT);
    udp.write((const uint8_t*)msg, strlen(msg));
    udp.endPacket();

    // Evidencia en serial
    Serial.print("RAW ");
    Serial.println(msg);

    seq++;
  }
}
```

### C2. Ejecutar y verificar

1. Cargar el sketch al ESP32.
2. Abrir monitor serial (115200).
3. Verificar que Cloud y Edge están ejecutándose en WSL.

Evidencias:

* Captura/copia del monitor serial mostrando líneas `RAW`.
* Consola de Edge mostrando `raw` y `events`.
* Consola de Cloud mostrando eventos `ANOM`.

---

## 9. Experimento de ajuste de umbral (en Edge Python)

1. Detener `edge.py` (Ctrl+C). Mantener `cloud.py` corriendo.
2. Editar `edge.py` y cambiar:

   * Caso 1: `Z_THRESHOLD = 2.0`
   * Caso 2: `Z_THRESHOLD = 4.0`
3. Reiniciar `edge.py` y medir por 60 segundos.

Tabla sugerida:

| Z_THRESHOLD | raw msgs/2s (aprox) | events/2s (aprox) | Observación |
| ----------: | ------------------: | ----------------: | ----------- |

---

## 10. Cuestionario (responder en el reporte)

1. ¿Qué se procesa en el borde y qué se deja a la nube en esta práctica?
2. ¿Qué cambia al modificar `Z_THRESHOLD` y por qué?
3. ¿Qué información mínima debe contener un evento para que sea útil?
4. Si se pierde conectividad, ¿qué harías para no perder eventos? (2–4 líneas)

---

## 11. Formato de reporte

1. Portada
2. Objetivos
3. Procedimiento (breve)
4. Evidencias (ESP32 serial + Edge + Cloud)
5. Resultados (tabla de umbrales)
6. Respuestas del cuestionario
7. Conclusiones (5–8 líneas)