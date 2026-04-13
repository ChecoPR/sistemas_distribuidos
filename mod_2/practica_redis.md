# Mensajería asíncrona con Redis

### **Asignatura:** Sistemas Distribuidos
### **Lenguaje:** Python 3.8+
### **Entregable:** Código fuente + informe de observaciones

---

## 1. ¿Qué es Redis?

Redis es un almacén de datos en memoria. Además de guardar valores clave, expone estructuras como listas y canales de mensajes que permiten comunicar procesos entre sí.

En esta práctica lo usamos como **broker**: un intermediario que recibe mensajes de un proceso y los entrega a otro. **¿cómo comunicas dos programas que no corren al mismo tiempo o que no se conocen entre sí?**

Construiremos dos sistemas distintos:

| Sistema | Patrón | Pregunta que responde |
|---------|--------|-----------------------|
| Cola de tareas | Productor → Cola → Consumidor | ¿Cómo proceso trabajo en diferido? |
| Canal de eventos | Publicador → Canal → N suscriptores | ¿Cómo notifico a varios procesos a la vez? |

---

## 2. Instalación

### Redis

```bash
# Ubuntu / Debian
sudo apt install redis-server
sudo systemctl start redis-server

# macOS
brew install redis && brew services start redis

# Windows — usar Docker
docker run -d -p 6379:6379 redis:latest
```

### Entorno virtual Python

En Ubuntu 23+ y Debian 12+, `pip` global está bloqueado por el sistema operativo.  
La solución es usar un entorno virtual. Hacerlo una sola vez por proyecto:

```bash
python3 -m venv venv
source venv/bin/activate
```

El prompt cambia a `(venv)`. Esto indica que el entorno está activo.  
Todos los comandos `pip` y `python3` que se ejecuten a partir de aquí instalan y usan paquetes dentro del entorno, sin tocar el sistema.

Para reactivarlo en una sesión nueva (no hace falta reinstalar nada):

```bash
source venv/bin/activate
```

### Biblioteca Python

Con el entorno activo:

```bash
pip install redis
```

### Verificar que todo funciona

```bash
python3 -c "import redis; r = redis.Redis(); print(r.ping())"
```

Salida esperada:

```
True
```

Si aparece `ConnectionRefusedError`, Redis no está corriendo. Verificar con:

```bash
systemctl status redis-server
```

---

## 3. Parte I — Cola de tareas

### ¿Qué problema resuelve?

Un proceso genera trabajo (el **productor**) y otro lo ejecuta (el **consumidor**). La cola los desacopla: el productor deposita tareas sin esperar a que alguien las procese. El consumidor las retira cuando puede.

Propiedades concretas de este patrón:

- **Persistencia**: la tarea queda en Redis hasta que un consumidor la retira. Si el consumidor se cae, las tareas no se pierden.
- **Un receptor por mensaje**: si hay varios consumidores, cada tarea va a exactamente uno. No hay duplicados.
- **Bloqueo eficiente**: el consumidor espera sin consumir CPU hasta que llegue una tarea.

### Estructura del sistema

| Archivo | Rol | Terminal |
|---------|-----|----------|
| `productor.py` | Genera tareas y las encola | Terminal 1 |
| `consumidor.py` | Extrae tareas y las procesa | Terminal 2 y 3 |
| `monitor.py` | Observa la cola sin consumirla | Terminal adicional |

---

### 3.1 `productor.py`

```python
import redis
import json
import time
import uuid
import random

TIPOS = ["normalizar_datos", "generar_reporte",
         "enviar_notificacion", "calcular_metrica"]

PRIORIDADES = ["alta", "media", "baja"]


def conectar():
    return redis.Redis(host="localhost", port=6379, decode_responses=True)


def crear_tarea(tipo, prioridad, payload):
    return {
        "id":        str(uuid.uuid4()),
        "tipo":      tipo,
        "prioridad": prioridad,
        "payload":   payload,
        "creada_en": time.time(),
    }


def main():
    r    = conectar()
    COLA = "cola:tareas"
    n    = 0

    print(f"Productor iniciado. Encolando en '{COLA}'.")
    print("Ctrl+C para detener.\n")

    try:
        while True:
            tipo      = random.choice(TIPOS)
            prioridad = random.choice(PRIORIDADES)
            payload   = {"parametro": random.randint(1, 1000)}
            tarea     = crear_tarea(tipo, prioridad, payload)

            # LPUSH inserta al frente de la lista.
            # BRPOP (en el consumidor) retira del fondo.
            # El par LPUSH/BRPOP implementa FIFO.
            r.lpush(COLA, json.dumps(tarea))

            n        += 1
            longitud  = r.llen(COLA)
            print(f"[{n:>4}] {tarea['id'][:8]}  "
                  f"{tipo:<24}  {prioridad:<6}  cola={longitud}")

            time.sleep(1.5)

    except KeyboardInterrupt:
        print(f"\nDetenido. Total encoladas: {n}")


if __name__ == "__main__":
    main()
```

**Qué hace cada parte:**

- `uuid.uuid4()` genera un identificador único para cada tarea. Permite rastrearla a lo largo del sistema.
- `time.time()` guarda el momento exacto en que se creó. El consumidor usará este valor para medir cuánto tiempo esperó la tarea.
- `r.llen(COLA)` consulta cuántos elementos hay en la lista en ese instante. Permite ver si la cola crece o se vacía.

---

### 3.2 `consumidor.py`

```python
import redis
import json
import time
import sys
import random


def conectar():
    return redis.Redis(host="localhost", port=6379, decode_responses=True)


def procesar(tarea, worker_id):
    # Simula trabajo real con una espera aleatoria.
    # En producción aquí iría la lógica de negocio.
    latencia = random.uniform(0.5, 2.0)
    time.sleep(latencia)
    return {
        "tarea_id":    tarea["id"],
        "worker":      worker_id,
        "procesada_en": time.time(),
        "latencia_s":  round(latencia, 3),
    }


def main(worker_id):
    r    = conectar()
    COLA = "cola:tareas"
    n    = 0

    print(f"Worker [{worker_id}] listo. Esperando en '{COLA}'.")
    print("Ctrl+C para detener.\n")

    try:
        while True:
            # BRPOP bloquea el proceso hasta que haya un elemento.
            # timeout=0 significa esperar indefinidamente sin consumir CPU.
            # Retorna una tupla (nombre_de_cola, datos).
            res = r.brpop(COLA, timeout=0)

            if res is None:
                continue

            _, datos = res
            tarea    = json.loads(datos)
            n       += 1

            espera = round(time.time() - tarea["creada_en"], 3)
            print(f"[{worker_id}] Procesando  {tarea['id'][:8]}  "
                  f"{tarea['tipo']:<24}  espera={espera}s")

            resultado = procesar(tarea, worker_id)
            print(f"[{worker_id}] Completada  {tarea['id'][:8]}  "
                  f"latencia={resultado['latencia_s']}s  total={n}")

    except KeyboardInterrupt:
        print(f"\n[{worker_id}] Detenido. Total procesadas: {n}")


if __name__ == "__main__":
    worker_id = sys.argv[1] if len(sys.argv) > 1 else "W1"
    main(worker_id)
```

**Por qué `BRPOP` y no `RPOP` en un bucle:**

`RPOP` requeriría llamar a Redis constantemente aunque la cola esté vacía, consumiendo CPU y red. `BRPOP` suspende el proceso en el servidor de Redis hasta que llegue un elemento. El proceso no usa CPU mientras espera.

---

### 3.3 `monitor.py`

```python
import redis
import json
import time


def main():
    r    = redis.Redis(host="localhost", port=6379, decode_responses=True)
    COLA = "cola:tareas"

    print("Monitor activo. Actualizando cada 2s. Ctrl+C para detener.\n")

    try:
        while True:
            longitud = r.llen(COLA)
            ts       = time.strftime("%H:%M:%S")
            print(f"[{ts}]  Tareas en cola: {longitud}")

            if longitud > 0:
                # lrange lee sin extraer (peek).
                # Índices 0..2 devuelven hasta 3 elementos.
                muestra = r.lrange(COLA, 0, 2)
                for raw in muestra:
                    t = json.loads(raw)
                    print(f"    {t['id'][:8]}  {t['tipo']:<24}  {t['prioridad']}")

            time.sleep(2)

    except KeyboardInterrupt:
        print("Monitor detenido.")


if __name__ == "__main__":
    main()
```

`lrange` lee elementos de la lista **sin retirarlos**. Eso distingue al monitor de un consumidor: observa sin interferir.

---

### 3.4 Ejecución — Parte I

Activar el entorno virtual en cada terminal antes de ejecutar:

```bash
source venv/bin/activate
```

**Terminal 1 — monitor:**
```bash
python3 monitor.py
```

**Terminal 2 — productor:**
```bash
python3 productor.py
```

El monitor debe mostrar la cola creciendo.

**Terminal 3 — primer consumidor:**
```bash
python3 consumidor.py W1
```

Observar cómo la cola empieza a vaciarse.

**Terminal 4 — segundo consumidor:**
```bash
python3 consumidor.py W2
```

Cada tarea llega a exactamente uno de los dos workers. La distribución no es determinista: depende de cuál ejecute `BRPOP` primero. Ese es el comportamiento correcto.

---

### 3.5 Preguntas — Parte I

Responder en el informe con evidencia del terminal.

1. Detén ambos consumidores con Ctrl+C. Deja el productor corriendo 30 segundos. Reinicia los consumidores. ¿Las tareas encoladas durante la caída se procesan o se pierden? Explica por qué.

2. Con el productor activo, inicia un tercer consumidor (`W3`). ¿Cómo cambia la distribución de tareas entre los tres? ¿Qué implicación tiene esto para escalar el sistema horizontalmente?

3. Modifica el productor para encolar 20 tareas sin pausa (elimina el `time.sleep`). Observa los tiempos de espera reportados por los consumidores. Describe el comportamiento bajo carga concentrada.

4. ¿Qué diferencia hay entre este patrón y llamar a una función que hace el trabajo directamente en el mismo proceso? Describe dos escenarios donde la cola es mejor y dos donde no vale la pena.

---

## 4. Parte II — Publicación/Suscripción

### ¿Qué problema resuelve?

El publicador emite un evento a un canal. Todos los procesos suscritos a ese canal reciben una copia simultáneamente. El publicador no sabe ni le importa quién está escuchando.

Diferencias clave respecto a la cola:

| Propiedad | Cola de tareas | Pub/Sub |
|-----------|---------------|---------|
| Persistencia | Sí: el mensaje espera en Redis | No: si no hay suscriptores, el mensaje se pierde |
| Receptores | Uno | Todos los suscritos activos |
| Tolerancia a caídas | Alta | Baja: el suscriptor caído pierde los mensajes |

### Estructura del sistema

| Archivo | Rol | Terminal |
|---------|-----|----------|
| `publicador.py` | Publica métricas de sistema | Terminal 1 |
| `suscriptor_dashboard.py` | Muestra métricas en tabla | Terminal 2 |
| `suscriptor_alertas.py` | Dispara alertas por umbral | Terminal 3 |
| `suscriptor_media_movil.py` | Calcula media móvil de CPU | Terminal 4 |

---

### 4.1 `publicador.py`

```python
import redis
import json
import time
import random
import sys

ORIGEN = sys.argv[1] if len(sys.argv) > 1 else "agente-default"


def crear_evento(canal, tipo, datos):
    # El esquema de este diccionario es el "contrato" del canal.
    # Publicador y suscriptores deben acordarlo de antemano.
    return {
        "canal":     canal,
        "tipo":      tipo,
        "timestamp": time.time(),
        "origen":    ORIGEN,
        "datos":     datos,
    }


def main():
    r     = redis.Redis(host="localhost", port=6379, decode_responses=True)
    CANAL = "eventos:sistema"
    n     = 0

    print(f"Publicador '{ORIGEN}' iniciado en canal '{CANAL}'.")
    print("Ctrl+C para detener.\n")

    try:
        while True:
            cpu   = round(max(0, min(100, random.gauss(45, 15))), 1)
            mem   = round(max(0, min(100, random.gauss(60, 10))), 1)
            disco = round(random.uniform(20, 85), 1)

            evento = crear_evento(CANAL, "metricas", {
                "cpu": cpu, "mem": mem, "disco": disco
            })

            # PUBLISH retorna cuántos suscriptores recibieron el mensaje.
            # 0 no es error: simplemente no hay nadie escuchando.
            receptores = r.publish(CANAL, json.dumps(evento))
            n         += 1

            print(f"[{n:>4}]  cpu={cpu}%  mem={mem}%  receptores={receptores}")

            time.sleep(2)

    except KeyboardInterrupt:
        print(f"\nPublicador detenido. Total publicados: {n}")


if __name__ == "__main__":
    main()
```

**Por qué `random.gauss` y no `random.randint`:**

`gauss(media, desviación)` genera valores con distribución normal: la mayoría caen cerca de la media y los extremos son raros. Eso imita mejor el comportamiento de una métrica real de CPU o memoria, donde los picos son infrecuentes.

---

### 4.2 `suscriptor_dashboard.py`

```python
import redis
import json
import time


def main():
    r  = redis.Redis(host="localhost", port=6379, decode_responses=True)
    ps = r.pubsub()

    # subscribe() registra este proceso como receptor del canal.
    # A partir de aquí, listen() entrega cada mensaje que llegue.
    ps.subscribe("eventos:sistema")

    print("Dashboard suscrito a 'eventos:sistema'.\n")
    print(f"{'Hora':<10}  {'CPU':>6}  {'Memoria':>9}  {'Disco':>7}")
    print("-" * 40)

    try:
        for mensaje in ps.listen():
            # Redis envía un primer mensaje de tipo 'subscribe'
            # como confirmación. Los mensajes reales son 'message'.
            if mensaje["type"] != "message":
                continue

            evento = json.loads(mensaje["data"])
            d      = evento["datos"]
            hora   = time.strftime("%H:%M:%S",
                                   time.localtime(evento["timestamp"]))

            alerta = "  <<< ALERTA" if d["cpu"] > 80 else ""
            print(f"{hora:<10}  {d['cpu']:>5}%  "
                  f"{d['mem']:>7}%  {d['disco']:>5}%{alerta}")

    except KeyboardInterrupt:
        print("\nDashboard detenido.")
    finally:
        ps.unsubscribe()
        ps.close()


if __name__ == "__main__":
    main()
```

---

### 4.3 `suscriptor_alertas.py`

```python
import redis
import json
import time

UMBRALES = {"cpu": 80.0, "mem": 85.0, "disco": 90.0}


def evaluar(evento):
    # Devuelve la lista de métricas que superaron su umbral.
    # Lista vacía significa que el evento es normal.
    alertas = []
    for metrica, limite in UMBRALES.items():
        valor = evento["datos"].get(metrica)
        if valor is not None and valor > limite:
            alertas.append(f"{metrica.upper()}={valor}%  (umbral={limite}%)")
    return alertas


def main():
    r  = redis.Redis(host="localhost", port=6379, decode_responses=True)
    ps = r.pubsub()

    # Suscripción simultánea a múltiples canales en una sola llamada.
    ps.subscribe("eventos:sistema", "eventos:aplicacion")

    print("Alertas activas en [eventos:sistema, eventos:aplicacion].\n")

    try:
        for mensaje in ps.listen():
            if mensaje["type"] != "message":
                continue

            evento  = json.loads(mensaje["data"])
            canal   = mensaje["channel"]
            alertas = evaluar(evento)

            if alertas:
                hora = time.strftime("%H:%M:%S",
                                     time.localtime(evento["timestamp"]))
                print(f"[{hora}]  ALERTA en '{canal}':")
                for a in alertas:
                    print(f"    {a}")
            # Sin alertas: el evento se descarta silenciosamente.

    except KeyboardInterrupt:
        print("\nServicio de alertas detenido.")
    finally:
        ps.unsubscribe()
        ps.close()


if __name__ == "__main__":
    main()
```

---

### 4.4 `suscriptor_media_movil.py`

Una **media móvil** calcula el promedio de los últimos N valores recibidos. Cuando llega un valor nuevo, el más antiguo sale del cálculo. Se usa para suavizar fluctuaciones y ver la tendencia real de una métrica.

`collections.deque` es la estructura adecuada para esto: cuando está llena y se agrega un elemento, el más antiguo se elimina automáticamente. El parámetro `maxlen` controla el tamaño de la ventana.

```python
import redis
import json
import time
from collections import deque


VENTANA = 5  # número de lecturas que entran en el promedio


def main():
    r  = redis.Redis(host="localhost", port=6379, decode_responses=True)
    ps = r.pubsub()
    ps.subscribe("eventos:sistema")

    # deque con maxlen=5: cuando está llena y se agrega un elemento,
    # el más antiguo se elimina automáticamente por el otro extremo.
    historial_cpu = deque(maxlen=VENTANA)

    print(f"Media móvil de CPU (ventana={VENTANA}). Ctrl+C para detener.\n")
    print(f"{'Hora':<10}  {'CPU actual':>12}  {'Media móvil':>13}")
    print("-" * 40)

    try:
        for mensaje in ps.listen():
            if mensaje["type"] != "message":
                continue

            evento = json.loads(mensaje["data"])
            cpu    = evento["datos"]["cpu"]
            hora   = time.strftime("%H:%M:%S",
                                   time.localtime(evento["timestamp"]))

            historial_cpu.append(cpu)

            # sum() y len() operan directamente sobre deque.
            media = sum(historial_cpu) / len(historial_cpu)

            # Mientras no haya VENTANA lecturas, la media usa las disponibles.
            lecturas = len(historial_cpu)
            sufijo   = f"  (acumulando {lecturas}/{VENTANA})" if lecturas < VENTANA else ""

            print(f"{hora:<10}  {cpu:>11}%  {media:>12.1f}%{sufijo}")

    except KeyboardInterrupt:
        print("\nMedia móvil detenida.")
    finally:
        ps.unsubscribe()
        ps.close()


if __name__ == "__main__":
    main()
```

**Cómo funciona `deque(maxlen=5)` paso a paso:**

```
Llega 45.2  →  [45.2]                          media = 45.2
Llega 38.7  →  [45.2, 38.7]                    media = 42.0
Llega 51.0  →  [45.2, 38.7, 51.0]              media = 45.0
Llega 43.5  →  [45.2, 38.7, 51.0, 43.5]        media = 44.6
Llega 60.1  →  [45.2, 38.7, 51.0, 43.5, 60.1]  media = 47.7
Llega 30.0  →  [38.7, 51.0, 43.5, 60.1, 30.0]  media = 44.7  ← 45.2 sale
```

El valor más antiguo (45.2) salió cuando llegó el sexto valor. La ventana siempre tiene como máximo 5 elementos.

---

### 4.5 Ejecución — Parte II

Activar el entorno virtual en cada terminal:

```bash
source venv/bin/activate
```

**Terminal 1 — dashboard:**
```bash
python3 suscriptor_dashboard.py
```

Queda en espera. No produce salida hasta recibir mensajes.

**Terminal 2 — alertas:**
```bash
python3 suscriptor_alertas.py
```

Igual, en espera.

**Terminal 3 — media móvil:**
```bash
python3 suscriptor_media_movil.py
```

Igual, en espera.

**Terminal 4 — publicador:**
```bash
python3 publicador.py
```

Las tres terminales deben recibir cada mensaje simultáneamente. El dashboard muestra todas las métricas. El servicio de alertas solo imprime cuando CPU > 80%, mem > 85% o disco > 90%. La media móvil muestra la tendencia de CPU suavizada.

**Escenario de caída:**

1. Detén el dashboard (Ctrl+C en Terminal 1).
2. Deja el publicador corriendo 30 segundos.
3. Reinicia el dashboard.

Observar que los mensajes publicados durante la caída no aparecen. Contrastar con el comportamiento de la cola en la Parte I.

---

### 4.6 Preguntas — Parte II

1. Detén todos los suscriptores y publica 10 mensajes. Reinicia los suscriptores. ¿Reciben esos mensajes? Explica la diferencia con lo observado en la Parte I.

2. Modifica `publicador.py` para que publique también en `eventos:aplicacion` cuando `cpu > 70%`, añadiendo un campo `"error_simulado": True` en los datos. Verifica que `suscriptor_alertas.py` recibe de ambos canales sin modificarlo.

3. Reduce el `time.sleep` del publicador a `0.1` segundos y añade `time.sleep(0.5)` dentro del bucle de `suscriptor_dashboard.py`. Describe qué ocurre y propón cómo resolverlo.

4. Observa la columna "Media móvil" en `suscriptor_media_movil.py` comparada con los valores individuales. ¿Cuándo es útil suavizar una métrica antes de tomar una decisión? ¿Cuándo sería perjudicial?

---

## 5. Comparación de patrones

| Propiedad | Cola de tareas | Pub/Sub |
|-----------|---------------|---------|
| Persistencia | Sí: permanece hasta consumirse | No: solo mientras hay suscriptores activos |
| Receptores por mensaje | Uno | Todos los suscritos activos |
| Tolerancia a caídas del receptor | Alta: el mensaje espera | Baja: los mensajes durante la caída se pierden |
| Orden de entrega | FIFO garantizado | Sin garantía entre canales |
| Primitiva Redis | `LPUSH` / `BRPOP` | `PUBLISH` / `SUBSCRIBE` |
| Equivalente en producción | RabbitMQ, AWS SQS | Kafka topics, WebSockets |

---

## 6. Entregable

### Informe

1. Respuestas a las preguntas de la Parte I (sección 3.5), con capturas de terminal.
2. Respuestas a las preguntas de la Parte II (sección 4.6), con capturas de terminal.
3. Comparación propia de ambos patrones aplicada a un sistema real que conozcas, distinto de los ejemplos de la guía.

Formato PDF.
