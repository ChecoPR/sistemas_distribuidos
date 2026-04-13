# cliente_grpc.py
import grpc
import calculadora_pb2, calculadora_pb2_grpc

with grpc.insecure_channel('localhost:50051') as canal:
    stub = calculadora_pb2_grpc.CalculadoraStub(canal)

    # Llamar Sumar
    resp = stub.Sumar(calculadora_pb2.ParNumeros(a=15, b=27))
    print(f"15 + 27 = {resp.valor}")

    # Llamar CalcularPrecio
    resp2 = stub.CalcularPrecio(
        calculadora_pb2.DatosPrecio(km=8, trafico='alto'))
    print(f"Precio: ${resp2.valor}")
