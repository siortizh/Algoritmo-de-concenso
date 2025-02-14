import grpc
from concurrent import futures
import raft_pb2_grpc
import raft_pb2
import os
import threading
import time

class LeaderService(raft_pb2_grpc.RaftServiceServicer):
    def __init__(self, follower_addresses):
        self.log = []  # Lista en memoria de las entradas
        self.last_id = 0  # Contador de IDs de las entradas
        self.log_file = "leader.txt"  # Archivo de log del líder
        self.follower_stubs = []  # Stubs de los followers
        self.heartbeat_interval = 2  # Intervalo para enviar latidos del corazón

        # Establecer conexiones con los followers
        for addr in follower_addresses:
            channel = grpc.insecure_channel(addr)
            stub = raft_pb2_grpc.RaftServiceStub(channel)
            self.follower_stubs.append(stub)

        # Asegurar que el archivo leader.txt existe
        if not os.path.exists(self.log_file):
            with open(self.log_file, "w") as f:
                f.write("ID\tEntrada\n")

        # Cargar el log desde el archivo al iniciar
        self.load_log_from_file()

        # Sincronizar el log al reconectarse
        self.sync_log_with_followers()

        # Iniciar hilo para enviar latidos del corazón
        self.heartbeat_thread = threading.Thread(target=self.send_heartbeat)
        self.heartbeat_thread.daemon = True
        self.heartbeat_thread.start()

    def load_log_from_file(self):
        """Carga el log del archivo en memoria."""
        with open(self.log_file, "r") as f:
            lines = f.readlines()[1:]  # Omitir la primera línea (encabezado)
            for line in lines:
                entry_id, entry = line.strip().split("\t", 1)
                self.log.append((int(entry_id), entry))
                self.last_id = max(self.last_id, int(entry_id))  # Actualizar last_id

    def sync_log_with_followers(self):
        for stub in self.follower_stubs:
            try:
                response = stub.GetState(raft_pb2.GetStateRequest())
                follower_log = response.state.splitlines()[1:]  # Omitir encabezado
                for line in follower_log:
                    # Validar si la línea tiene el formato correcto
                    if "\t" not in line:
                        print(f"Advertencia: Línea mal formateada ignorada: '{line}'")
                        continue  # Ignorar líneas mal formateadas

                    entry_id, entry = line.split("\t", 1)
                    entry_id = int(entry_id)

                    # Si el líder no tiene esta entrada, la añade
                    if entry_id > self.last_id:
                        print(f"Sincronizando entrada faltante: {entry}")
                        self.log.append((entry_id, entry))
                        with open(self.log_file, "a") as f:
                            f.write(f"{entry_id}\t{entry}\n")
                        self.last_id = entry_id
            except grpc.RpcError as e:
                print(f"Error al sincronizar con follower: {e}")


    def AppendEntries(self, request, context):
        """Registrar entradas nuevas y replicarlas en los followers."""
        response_entries = []
        for entry in request.entries:
            self.last_id += 1
            log_entry = f"{self.last_id}\t{entry}\n"
            
            # Guardar en el archivo del líder
            with open(self.log_file, "a") as f:
                f.write(log_entry)

            # Guardar en el log en memoria
            self.log.append((self.last_id, entry))
            response_entries.append(log_entry.strip())  # Preparar para enviar a los followers

        # Enviar las entradas a todos los followers
        append_request = raft_pb2.AppendEntriesRequest(entries=response_entries)
        for stub in self.follower_stubs:
            try:
                response = stub.AppendEntries(append_request)
                if response.success:
                    print(f"Entrada replicada exitosamente en un follower: {response_entries}")
            except grpc.RpcError as e:
                print(f"Error al replicar entrada en follower: {e}")

        return raft_pb2.AppendEntriesResponse(success=True)


    def send_heartbeat(self):
        """Envía latidos del corazón a los followers periódicamente."""
        while True:
            heartbeat_request = raft_pb2.AppendEntriesRequest(entries=[])
            for stub in self.follower_stubs:
                try:
                    stub.AppendEntries(heartbeat_request)
                except grpc.RpcError as e:
                    print(f"Error al enviar latido del corazón: {e}")
            print("Enviando latido del corazón a los followers.")
            time.sleep(self.heartbeat_interval)

def serve():
    port = 50052
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    follower_addresses = ['172.31.41.96:50054', '172.31.33.34:50055']
    raft_pb2_grpc.add_RaftServiceServicer_to_server(LeaderService(follower_addresses), server)
    server.add_insecure_port(f'[::]:{port}')
    server.start()
    print("Servidor de líder en ejecución en el puerto 50052...")
    server.wait_for_termination()

if __name__ == "__main__":
    serve()