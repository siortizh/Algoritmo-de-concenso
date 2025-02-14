import grpc
import proxy_pb2_grpc
import proxy_pb2
import raft_pb2_grpc
import raft_pb2
import concurrent.futures as futures
import time
import random 

class ProxyService(proxy_pb2_grpc.ProxyServiceServicer):
    def __init__(self, leader_address, follower_addresses):
        self.leader_address = leader_address
        self.follower_addresses = follower_addresses
        self.leader_stub = None
        self.follower_stubs = []

        self.update_leader_stub()  # Establecer la conexión con el líder
        self.update_follower_stubs()  # Establecer la conexión con los followers

    def update_leader_stub(self):
        try:
            self.leader_channel = grpc.insecure_channel(self.leader_address)
            grpc.channel_ready_future(self.leader_channel).result(timeout=2)
            self.leader_stub = raft_pb2_grpc.RaftServiceStub(self.leader_channel)
            print(f"Conectado al líder en {self.leader_address}")
        except grpc.FutureTimeoutError:
            print(f"No se pudo conectar al líder en {self.leader_address}. Buscando nuevo líder...")
            self.find_new_leader()

    def update_follower_stubs(self):
        self.follower_channels = [grpc.insecure_channel(addr) for addr in self.follower_addresses]
        self.follower_stubs = [raft_pb2_grpc.RaftServiceStub(channel) for channel in self.follower_channels]

    def find_new_leader(self, retries=5, interval=2):
        for attempt in range(retries):
            print(f"Intentando encontrar un nuevo líder... (Intento {attempt + 1}/{retries})")
            for idx, stub in enumerate(self.follower_stubs):
                try:
                    response = stub.GetState(raft_pb2.GetStateRequest())
                    if "líder" in response.state.lower():  # Verificar si es el nuevo líder
                        self.leader_address = self.follower_addresses[idx]
                        self.update_leader_stub()
                        print(f"Nuevo líder detectado en {self.leader_address}")
                        return
                except grpc.RpcError:
                    print(f"Follower en {self.follower_addresses[idx]} no respondió.")

            time.sleep(interval)  # Esperar antes del próximo intento

        print("No se pudo encontrar un nuevo líder.")

    def Write(self, request, context):
        if self.leader_stub is None:
            self.update_leader_stub()

        if self.leader_stub:
            append_request = raft_pb2.AppendEntriesRequest(entries=[request.data])
            print(f"Enviando solicitud de escritura (write) al líder en {self.leader_address}")

            try:
                leader_response = self.leader_stub.AppendEntries(append_request)
                if leader_response.success:
                    return proxy_pb2.WriteResponse(success=True)
                else:
                    return proxy_pb2.WriteResponse(success=False)
            except grpc.RpcError as e:
                print(f"Error al escribir en el líder: {e}")
                self.find_new_leader()  # Intentar encontrar un nuevo líder
                return proxy_pb2.WriteResponse(success=False)
        else:
            print("No se pudo conectar al líder para realizar la escritura.")
            return proxy_pb2.WriteResponse(success=False)

    def Read(self, request, context):
        """Redirigir lectura a uno de los followers al azar"""
        follower_stub = random.choice(self.follower_stubs)  # Elegir un follower al azar
        follower_address = self.follower_addresses[self.follower_stubs.index(follower_stub)]
        print(f"Enviando solicitud de lectura (read) al follower en {follower_address}")

        try:
            response = follower_stub.GetState(raft_pb2.GetStateRequest())
            return proxy_pb2.ReadResponse(data=response.state)
        except grpc.RpcError as e:
            print(f"Error al leer de un follower: {e}")
            return proxy_pb2.ReadResponse(data="Error al leer de follower.")

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    # Direcciones del líder y followers
    leader_address = '172.31.47.254:50052'
    follower_addresses = ['172.31.41.96:50054', '172.31.33.34:50055']

    proxy_service = ProxyService(leader_address, follower_addresses)
    proxy_pb2_grpc.add_ProxyServiceServicer_to_server(proxy_service, server)
    server.add_insecure_port('[::]:50051')
    print("Servidor de proxy en ejecución en el puerto 50051...")
    server.start()
    server.wait_for_termination()

if __name__ == "__main__":
    serve()