import grpc
from concurrent import futures
import raft_pb2_grpc
import raft_pb2
import os
import time
import threading
import random

class FollowerService(raft_pb2_grpc.RaftServiceServicer):
    def __init__(self, peer_addresses):
        self.term = 0
        self.voted_for = None
        self.log = []
        self.log_file = f"follower2.txt"
        self.is_leader = False
        self.leader_alive = True
        self.election_timeout = random.uniform(5, 10)
        self.peer_stubs = []
        self.peer_addresses = peer_addresses
        self.votes_received = 0

        # Establecer conexiones con otros followers
        for addr in self.peer_addresses:
            channel = grpc.insecure_channel(addr)
            stub = raft_pb2_grpc.RaftServiceStub(channel)
            self.peer_stubs.append(stub)

        # Asegurar que el archivo follower.txt existe
        if not os.path.exists(self.log_file):
            with open(self.log_file, "w") as f:
                f.write("ID\tEntrada\n")

        # Iniciar hilo para monitorear el líder
        self.heartbeat_thread = threading.Thread(target=self.monitor_leader)
        self.heartbeat_thread.daemon = True
        self.heartbeat_thread.start()

    def AppendEntries(self, request, context):
        self.leader_alive = True
        self.voted_for = None  # Resetear la votación si se recibe latido
        print(f"Follower 2 ha recibido latido del líder en el término {self.term}")
        
        if request.entries:
            with open(self.log_file, "a") as f:
                for entry in request.entries:
                    entry_id, entry_text = entry.split("\t", 1)
                    formatted_entry = f"{entry_id}\t{entry_text}\n"
                    f.write(formatted_entry)

        # Reiniciar el temporizador del líder
        self.leader_alive = True  
        return raft_pb2.AppendEntriesResponse(success=True)

    def RequestVote(self, request, context):
        if self.voted_for is None or request.term > self.term:
            self.term = request.term
            self.voted_for = request.candidate_id
            print(f"Follower 2 ha votado por el candidato {request.candidate_id} en el término {self.term}")
            return raft_pb2.RequestVoteResponse(term=self.term, vote_granted=True)
        else:
            print(f"Follower 2 rechazó la solicitud de voto de {request.candidate_id} porque ya votó por {self.voted_for}")
            return raft_pb2.RequestVoteResponse(term=self.term, vote_granted=False)

    def monitor_leader(self):
        while True:
            time.sleep(self.election_timeout)
            if not self.leader_alive:
                print("No se detecta líder. Iniciando una elección...")
                self.start_election()
            else:
                self.leader_alive = False  # Reset del temporizador de latido

    def start_election(self):
        time.sleep(random.uniform(0.5, 1.5))
        
        self.term += 1  # Incrementa el término
        self.voted_for = "follower 2"  # Reiniciar la votación
        self.votes_received = 1  # Se vota a sí mismo
        print(f"Iniciando proceso de elección en el término {self.term}")

        # Enviar solicitud de votos a otros followers
        for stub in self.peer_stubs:
            try:
                vote_request = raft_pb2.RequestVoteRequest(term=self.term, candidate_id="follower 2")
                response = stub.RequestVote(vote_request)
                if response.vote_granted:
                    self.votes_received += 1
                    print(f"Follower 2 recibió un voto. Total de votos: {self.votes_received}")
            except grpc.RpcError as e:
                print(f"Error al solicitar votos: {e}")

        # Convertirse en líder si recibe la mayoría de votos
        if self.votes_received > len(self.peer_stubs) // 2:
            self.is_leader = True
            print(f"Follower 2 se ha convertido en el nuevo líder en el término {self.term}")
            self.send_heartbeat()
        else:
            print(f"Follower 2 no ha recibido suficientes votos en el término {self.term}")

    def send_heartbeat(self):
        while self.is_leader:
            if self.leader_alive:
                print("El líder original ha regresado. Volviendo al estado de follower.")
                self.is_leader = False
                return

            heartbeat_request = raft_pb2.AppendEntriesRequest(entries=[])

            try:
                stub = self.peer_stubs[1]  
                stub.AppendEntries(heartbeat_request)
                print("Enviando latido del corazón al follower 1.")
            except IndexError:
                print("Error: No se encontró el follower 1 en peer_stubs.")
            except grpc.RpcError as e:
                print(f"Error al enviar latido del corazón: {e}")
            
            time.sleep(2)

    def GetState(self, request, context):
        with open(self.log_file, "r") as f:
            state = f.read()
        return raft_pb2.GetStateResponse(state=state)

def serve(peer_addresses, port):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    raft_pb2_grpc.add_RaftServiceServicer_to_server(FollowerService(peer_addresses), server)
    server.add_insecure_port(f'[::]:{port}')
    print(f"Servidor de Follower 2 en ejecución en el puerto {port}...")
    server.start()
    server.wait_for_termination()

if __name__ == "__main__":
    peer_addresses = ['172.31.47.254:50052', '172.31.41.96:50054']  # IP Leader e IP Follower 1
    serve(peer_addresses=peer_addresses, port=50055)