# cliente_rpc.py
import xmlrpc.client

# ── PASO 1: Crear el proxy ──────────────────────────────────
# ServerProxy crea un objeto que 'imita' al servidor.
# Cuando llamas sus métodos, en realidad van a la red.
servidor = xmlrpc.client.ServerProxy('http://localhost:8000')

# ── PASO 2: Llamar funciones remotas (igual que locales) ────
resultado = servidor.sumar(15, 27)
print(f"15 + 27 = {resultado}")          # → 42

precio = servidor.calcular_precio(8, 'alto')
print(f"Viaje 8km tráfico alto: ${precio}")  # → $60.0

info = servidor.informacion_servidor()
print(f"Info del servidor: {info}")
# ── PASO 3: Manejo de errores ───────────────────────────────
try:
    resultado = servidor.funcion_inexistente()
except Exception as e:
    print(f"Error esperado: {e}")

# ── PASO 4: Ver qué funciones ofrece el servidor ────────────
funciones = servidor.system.listMethods()
print(f"Funciones disponibles: {funciones}")
