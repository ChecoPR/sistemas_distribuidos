# servidor_grpc.py
import grpc
from concurrent import futures
import calculadora_pb2, calculadora_pb2_grpc

class CalculadoraService(calculadora_pb2_grpc.CalculadoraServicer):
    def Sumar(self, request, context):
        total = request.a + request.b
        return calculadora_pb2.Resultado(valor=total)

    def CalcularPrecio(self, request, context):
        base = request.km * 5.0
        if request.trafico == 'alto': base *= 1.5
        return calculadora_pb2.Resultado(valor=round(base, 2))

def iniciar():
    servidor = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    calculadora_pb2_grpc.add_CalculadoraServicer_to_server(
        CalculadoraService(), servidor)
    servidor.add_insecure_port('[::]:50051')
    servidor.start()
    print("Servidor gRPC en puerto 50051...")
    servidor.wait_for_termination()

if __name__ == '__main__': iniciar()
