#!/usr/bin/env python3

from concurrent import futures
import os
import time
import random
import grpc
import threading
import itertools

# Import des fichiers générés
import cat_pb2
import cat_pb2_grpc
import mouse_pb2
import mouse_pb2_grpc

# Variables d'environnement
CAT_ID = os.environ.get("CAT_ID", "cat")
CLUSTER_NODES = os.environ.get("CLUSTER_NODES", "mouse").split(",")
PEER_CATS = os.environ.get("PEER_CATS", "cat1,cat2,cat3").split(",")
CAT_SERVICE_PORT = int(os.environ.get("CAT_SERVICE_PORT", 60000))

PORT_MIN = 50000
PORT_MAX = 50100


class CatState:
    def __init__(self):
        self.mouse_found = None
        self.captured = False
        self.lock = threading.Lock()

    def set_mouse_found(self, node, port):
        with self.lock:
            if self.mouse_found is None:
                self.mouse_found = (node, port)
                return True
            return False

    def get_mouse_found(self):
        with self.lock:
            return self.mouse_found

    def set_captured(self, status):
        with self.lock:
            self.captured = status

    def is_captured(self):
        with self.lock:
            return self.captured


state = CatState()


class CatServiceServicer(cat_pb2_grpc.CatServiceServicer):
    def Notify(self, request, context):
        if state.set_mouse_found(request.node, request.port):
            print(
                f"[{CAT_ID}] Notification reçue : souris sur {request.node} au port {request.port}"
            )
            attempt_capture(request.node, request.port)
        return cat_pb2.Ack(message="Notification reçue")


def start_cat_server():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=5))
    cat_pb2_grpc.add_CatServiceServicer_to_server(CatServiceServicer(), server)

    server.add_insecure_port(f"[::]:{CAT_SERVICE_PORT}")
    print(f"[{CAT_ID}] Serveur CatService lancé sur le port {CAT_SERVICE_PORT}")
    server.start()

    return server


def simulate_animal_services():
    while True:
        time.sleep(1)
        if random.random() < 0.01:
            if not state.is_captured():
                state.set_captured(True)
                print(f"[Animal Services] Capture du {CAT_ID}!")
                threading.Timer(3, release_capture).start()


def release_capture():
    state.set_captured(False)
    print(f"[Animal Services] Libération du {CAT_ID}.")


def attempt_capture(node, port):
    try:
        channel = grpc.insecure_channel(f"{node}:{port}")
        stub = mouse_pb2_grpc.MouseServiceStub(channel)
        response = stub.Catch(mouse_pb2.Empty(), timeout=1)
        print(f"[{CAT_ID}] Souris attrapée : {response.message}")
    except Exception as e:
        print(f"[{CAT_ID}] Échec de l'attrape sur {node}:{port} : {e}")


def notify_peers(node, port):
    for peer in PEER_CATS:
        # Éviter de notifier soi-même
        if peer.strip() == CAT_ID:
            continue

        try:
            channel = grpc.insecure_channel(f"{peer.strip()}:{CAT_SERVICE_PORT}")
            stub = cat_pb2_grpc.CatServiceStub(channel)
            response = stub.Notify(
                cat_pb2.MouseLocation(node=node, port=port), timeout=1
            )
            print(f"[{CAT_ID}] Notification envoyée à {peer} : {response.message}")
        except Exception as e:
            print(f"[{CAT_ID}] Erreur lors de la notification à {peer} : {e}")


def scan_for_mouse():
    idx = 0
    node_port = list(itertools.product(CLUSTER_NODES, range(PORT_MIN, PORT_MAX + 1)))

    while True:
        # Si la souris a déjà été détectée, utiliser cette info et tenter l'attrape
        found = state.get_mouse_found()
        if found is not None:
            (node, port) = found
            print(f"[{CAT_ID}] Utilisation de l'info reçue : {node} sur le port {port}")
            attempt_capture(node, port)
            return

        if not state.is_captured():
            (node, port) = node_port[idx]
            idx = (idx + 1) % len(node_port)

            try:
                channel = grpc.insecure_channel(f"{node}:{port}")
                stub = mouse_pb2_grpc.MouseServiceStub(channel)
                response = stub.Meow(mouse_pb2.Empty(), timeout=0.5)
                if response.message.strip() == "SQUIIIIIK":
                    if state.set_mouse_found(node, port):
                        print(f"[{CAT_ID}] Souris détectée sur {node} au port {port}.")
                        # Notifier les autres chats via gRPC
                        notify_peers(node, port)
                        attempt_capture(node, port)
                    return
            except Exception:
                pass

        time.sleep(0.1)


if __name__ == "__main__":
    server = start_cat_server()

    # Démarrage de la simulation d'Animal Services
    t_services = threading.Thread(target=simulate_animal_services, daemon=True)
    t_services.start()

    # Démarrage du scan
    print(f"[{CAT_ID}] Démarrage du scan sur les noeuds : {CLUSTER_NODES}")
    scan_for_mouse()

    server.wait_for_termination()
