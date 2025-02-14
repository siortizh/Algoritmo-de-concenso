import grpc
import proxy_pb2_grpc
import proxy_pb2
import sys

class Client:
    def __init__(self, proxy_address):
        try:
            self.channel = grpc.insecure_channel(proxy_address)
            grpc.channel_ready_future(self.channel).result(timeout=5)  # Esperar conexión por 5 segundos
            self.stub = proxy_pb2_grpc.ProxyServiceStub(self.channel)
            print("Conectado al proxy en", proxy_address)
        except grpc.FutureTimeoutError:
            print(f"No se pudo conectar al proxy en {proxy_address}.")
            sys.exit()

    def write(self, data):
        request = proxy_pb2.WriteRequest(data=data)
        try:
            response = self.stub.Write(request)
            if response.success:
                print("Escritura exitosa.")
            else:
                print("Error al escribir en la base de datos.")
        except grpc.RpcError as e:
            print(f"Error de gRPC: {e}")

    def read(self):
        request = proxy_pb2.ReadRequest()
        try:
            response = self.stub.Read(request)
            print("Datos leídos:", response.data)
        except grpc.RpcError as e:
            print(f"Error de gRPC: {e}")

def menu():
    print("\nSeleccione una opción:")
    print("1. Escribir en la base de datos")
    print("2. Leer de la base de datos")
    print("3. Salir")
    return input("Opción: ")

if __name__ == "__main__":
    client = Client('172.31.45.74:50051')

    while True:
        opcion = menu()

        if opcion == "1":
            data = input("Ingrese los datos a escribir: ")
            client.write(data)

        elif opcion == "2":
            client.read()

        elif opcion == "3":
            print("Saliendo...")
            break

        else:
            print("Opción no válida. Por favor, seleccione una opción válida.")