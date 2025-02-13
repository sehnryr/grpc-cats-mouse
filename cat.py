#!/usr/bin/env python3

from concurrent import futures
import os
import time
import grpc
import random
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
        # remove peer cats from cluster nodes
        mouse_nodes = list(filter(lambda node: node not in PEER_CATS, CLUSTER_NODES))

        self.mouse_found = None
        self.captured = False
        self.lock = threading.Lock()
        self.node_port = list(
            itertools.product(mouse_nodes, range(PORT_MIN, PORT_MAX + 1))
        )

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

    def handle_capture(self, duration):
        self.set_captured(True)
        threading.Timer(duration, self.release_capture).start()

    def release_capture(self):
        self.set_captured(False)

    def get_node_port(self):
        idx = random.randint(0, len(self.node_port) - 1)
        return self.node_port.pop(idx)

    def delete_node_port(self, node, port):
        try:
            self.node_port.remove((node, port))
        except ValueError:
            pass


state = CatState()


class CatServiceServicer(cat_pb2_grpc.CatServiceServicer):
    def PortRead(self, request, context):
        state.delete_node_port(request.node, request.port)
        return cat_pb2.Ack(message="Notification reçue")

    def Notify(self, request, context):
        if state.set_mouse_found(request.node, request.port):
            print(
                f"[{CAT_ID}] Notification reçue : souris sur {request.node} au port {request.port}"
            )
            attempt_capture(request.node, request.port)
        return cat_pb2.Ack(message="Notification reçue")

    def CaptureNotification(
        self, request: cat_pb2.CaptureRequest, context: grpc.ServicerContext
    ) -> cat_pb2.CaptureAck:
        # Lorsqu'un chat reçoit cette notification, il passe en mode capturé.
        state.handle_capture(request.capture_duration)
        return cat_pb2.CaptureAck(
            message=f"{CAT_ID} capturé pour {request.capture_duration} secondes"
        )


def start_cat_server():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=5))
    cat_pb2_grpc.add_CatServiceServicer_to_server(CatServiceServicer(), server)

    server.add_insecure_port(f"[::]:{CAT_SERVICE_PORT}")
    print(f"[{CAT_ID}] Serveur CatService lancé sur le port {CAT_SERVICE_PORT}")
    server.start()

    return server


def attempt_capture(node, port):
    try:
        channel = grpc.insecure_channel(f"{node}:{port}")
        stub = mouse_pb2_grpc.MouseServiceStub(channel)
        response = stub.Catch(mouse_pb2.Empty(), timeout=1)
        print(f"[{CAT_ID}] Souris attrapée : {response.message}")
    except Exception as e:
        print(f"[{CAT_ID}] Échec de l'attrape sur {node}:{port} : {e}")


def notify_peers(node, port, captured):
    for peer in PEER_CATS:
        # Éviter de notifier soi-même
        if peer.strip() == CAT_ID:
            continue

        while True:
            try:
                channel = grpc.insecure_channel(f"{peer.strip()}:{CAT_SERVICE_PORT}")
                stub = cat_pb2_grpc.CatServiceStub(channel)

                if captured:
                    response = stub.Notify(
                        cat_pb2.MouseLocation(node=node, port=port), timeout=1
                    )
                    print(
                        f"[{CAT_ID}] Notification envoyée à {peer} : {response.message}"
                    )
                else:
                    stub.PortRead(
                        cat_pb2.MouseLocation(node=node, port=port), timeout=1
                    )
                break
            except Exception:
                time.sleep(0.1)
                continue


def scan_for_mouse():
    while True:
        # Si la souris a déjà été détectée, utiliser cette info et tenter l'attrape
        found = state.get_mouse_found()
        if found is not None:
            (node, port) = found
            print(f"[{CAT_ID}] Utilisation de l'info reçue : {node} sur le port {port}")
            attempt_capture(node, port)
            return

        if not state.is_captured():
            try:
                (node, port) = state.get_node_port()
            except IndexError:
                print(f"[{CAT_ID}] Aucune souris trouvée.")
                return

            print(f"[{CAT_ID}] Tentative de connexion à {node} sur le port {port}")

            try:
                channel = grpc.insecure_channel(f"{node}:{port}")
                stub = mouse_pb2_grpc.MouseServiceStub(channel)
                response = stub.Meow(mouse_pb2.Empty(), timeout=0.5)

                if response.message.strip() == "SQUIIIIIK":
                    if state.set_mouse_found(node, port):
                        print(f"[{CAT_ID}] Souris détectée sur {node} au port {port}.")
                        # Notifier les autres chats via gRPC
                        notify_peers(node, port, captured=True)
                        attempt_capture(node, port)
                    return
            except Exception:
                notify_peers(node, port, captured=False)

        time.sleep(0.1)


if __name__ == "__main__":
    server = start_cat_server()

    # Démarrage du scan
    print(f"[{CAT_ID}] Démarrage du scan sur les noeuds : {CLUSTER_NODES}")
    scan_for_mouse()

    server.wait_for_termination()
