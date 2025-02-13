#!/usr/bin/env python3

import os
import random
import time
import grpc

import cat_pb2
import cat_pb2_grpc

CAT_HOSTS = os.environ.get("CAT_HOSTS", "cat1,cat2,cat3").split(",")


def push_capture_notifications():
    if not CAT_HOSTS:
        print("[Animal Services] Aucun chat disponible pour la capture")
        return

    while True:
        if random.random() <= 0.01:
            selected_cat = random.choice(CAT_HOSTS)
            capture_duration = 3
            try:
                channel = grpc.insecure_channel(f"{selected_cat}:60000")
                stub = cat_pb2_grpc.CatServiceStub(channel)
                request = cat_pb2.CaptureRequest(
                    cat_id=selected_cat, capture_duration=capture_duration
                )
                response = stub.CaptureNotification(request, timeout=1)
                print(
                    f"[Animal Services] Notification de capture envoyée à {selected_cat}: {response.message}"
                )
            except Exception as e:
                print(
                    f"[Animal Services] Erreur lors de l'envoi de la notification à {selected_cat}: {e}"
                )

        time.sleep(1)


if __name__ == "__main__":
    push_capture_notifications()
