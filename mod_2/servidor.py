# Importamos el servidor xmlrpc (incluido en Python)
from xmlrpc.server import SimpleXMLRPCServer
import math

# ── PASO 1: Definir las funciones que exponemos ─────────────
# Estas funciones correrán en este servidor pero el cliente
# las llamará como si fueran locales en su máquina.

def sumar(a, b):
    """Suma dos números."""
    return a + b

def calcular_precio(km, trafico):
    """Simula el algoritmo de precio de Uber."""
    base = km * 5.0
    if trafico == 'alto':
        base *= 1.5   # surge pricing
    elif trafico == 'bajo':
        base *= 0.9
    return round(base, 2)

def informacion_servidor():
    """Retorna información del servidor."""
    return {"version": "1.0", "funciones": 3, "estado": "activo"}

# ── PASO 2: Crear y configurar el servidor ──────────────────
servidor = SimpleXMLRPCServer(
    ('localhost', 8000),
    allow_none=True)   # permite retornar None

# ── PASO 3: Registrar las funciones para exponerlas ─────────
servidor.register_function(sumar)
servidor.register_function(calcular_precio)
servidor.register_function(informacion_servidor)
# También puedes registrar con nombre diferente:
# servidor.register_function(sumar, 'add')

# ── PASO 4: Arrancar el servidor ────────────────────────────
print("Servidor RPC escuchando en puerto 8000...")
print("Funciones disponibles: sumar, calcular_precio, informacion_servidor")
print("Ctrl+C para detener\n")
servidor.serve_forever()   # bloquea aquí — como accept() en sockets
