#!/usr/bin/env python3

from concurrent import futures
import os
import time
import random
import grpc
import threading

# Import des fichiers générés
import mouse_pb2
import mouse_pb2_grpc
import cat_pb2
import cat_pb2_grpc

# Variables d'environnement
CAT_ID = os.environ.get("CAT_ID", "cat")
# Liste des nœuds du cluster à scanner (ex. "mouse,cat1,cat2,cat3")
CLUSTER_NODES = os.environ.get("CLUSTER_NODES", "mouse").split(",")
# Liste des pairs (tous les chats), dont le conteneur se reconnaît lui-même (sera filtré)
PEER_CATS = os.environ.get("PEER_CATS", "cat1,cat2,cat3").split(",")
# Adresse et port interne du service Cat (fixe)
CAT_SERVICE_PORT = int(os.environ.get("CAT_SERVICE_PORT", 60000))

# Plage des ports du service Mouse
PORT_MIN = 50000
PORT_MAX = 50100

# Variables de synchronisation et état
mouse_found = None
capture_lock = threading.Lock()
captured = False


# --- Partie serveur gRPC pour recevoir les notifications de pair ---
class CatServiceServicer(cat_pb2_grpc.CatServiceServicer):
    def Notify(self, request, context):
        global mouse_found
        with capture_lock:
            if mouse_found is None:
                mouse_found = (request.node, request.port)
                print(
                    f"[{CAT_ID}] Notification reçue : souris sur {request.node} au port {request.port}"
                )
                # Démarrage immédiat de l'attrape
                attempt_capture(request.node, request.port)
        return cat_pb2.Ack(message="Notification reçue")


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=5))
    cat_pb2_grpc.add_CatServiceServicer_to_server(CatServiceServicer(), server)

    server.add_insecure_port(f"[::]:{CAT_SERVICE_PORT}")
    print(f"[{CAT_ID}] Serveur CatService lancé sur le port {CAT_SERVICE_PORT}")
    server.start()

    return server


# --- Simulation d'Animal Services (capture aléatoire) ---
def simulate_animal_services():
    global captured
    while True:
        time.sleep(1)
        if random.random() < 0.01:
            with capture_lock:
                if not captured:
                    captured = True
                    print(f"[Animal Services] Capture du {CAT_ID}!")
                    threading.Timer(3, release_capture).start()


def release_capture():
    global captured
    with capture_lock:
        captured = False
    print(f"[Animal Services] Libération du {CAT_ID}.")


def is_captured():
    with capture_lock:
        return captured


# --- Fonction d'attrape de la souris ---
def attempt_capture(node, port):
    try:
        channel = grpc.insecure_channel(f"{node}:{port}")
        stub = mouse_pb2_grpc.MouseServiceStub(channel)
        response = stub.Catch(mouse_pb2.Empty(), timeout=1)
        print(f"[{CAT_ID}] Souris attrapée : {response.message}")
    except Exception as e:
        print(f"[{CAT_ID}] Échec de l'attrape sur {node}:{port} : {e}")


# --- Notification aux pairs via gRPC ---
def notify_peers(node, port):
    for peer in PEER_CATS:
        # Éviter de notifier soi-même
        if peer.strip() == CAT_ID:
            continue
        try:
            channel = grpc.insecure_channel(
                f"{peer.strip()}:{CAT_SERVICE_PORT}",
                options=(("grpc.enable_http_proxy", 0),),
            )
            stub = cat_pb2_grpc.CatServiceStub(channel)
            response = stub.Notify(
                cat_pb2.MouseLocation(node=node, port=port), timeout=1
            )
            print(f"[{CAT_ID}] Notification envoyée à {peer} : {response.message}")
        except Exception as e:
            print(f"[{CAT_ID}] Erreur lors de la notification à {peer} : {e}")


# --- Boucle principale de scan ---
def scan_for_mouse():
    global mouse_found
    while True:
        # Si une notification a déjà été reçue, tenter l'attrape et sortir
        with capture_lock:
            if mouse_found is not None:
                (node, port) = mouse_found
                print(
                    f"[{CAT_ID}] Utilisation de l'info reçue : {node} sur le port {port}"
                )
                attempt_capture(node, port)
                return

        if is_captured():
            time.sleep(0.1)
            continue

        # Parcourir les nœuds et les ports pour détecter la souris
        for node in CLUSTER_NODES:
            for port in range(PORT_MIN, PORT_MAX + 1):
                if is_captured():
                    break
                try:
                    channel = grpc.insecure_channel(f"{node}:{port}")
                    stub = mouse_pb2_grpc.MouseServiceStub(channel)
                    response = stub.Meow(mouse_pb2.Empty(), timeout=0.5)
                    if response.message.strip() == "SQUIIIIIK":
                        with capture_lock:
                            if mouse_found is None:
                                mouse_found = (node, port)
                                print(
                                    f"[{CAT_ID}] Souris détectée sur {node} au port {port}."
                                )
                                # Notifier les autres chats via gRPC
                                notify_peers(node, port)
                        attempt_capture(node, port)
                        return
                except Exception:
                    pass
                time.sleep(0.1)
        time.sleep(0.5)


if __name__ == "__main__":
    server = serve()

    # Démarrage de la simulation d'Animal Services
    t_services = threading.Thread(target=simulate_animal_services, daemon=True)
    t_services.start()
    print(f"[{CAT_ID}] Démarrage du scan sur les noeuds : {CLUSTER_NODES}")
    scan_for_mouse()

    server.wait_for_termination()
