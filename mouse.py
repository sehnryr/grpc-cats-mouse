#!/usr/bin/env python3

from concurrent import futures
import grpc
import random

import mouse_pb2
import mouse_pb2_grpc


class MouseServiceServicer(mouse_pb2_grpc.MouseServiceServicer):
    def Meow(self, request, context):
        return mouse_pb2.Reply(message="SQUIIIIIK")

    def Catch(self, request, context):
        return mouse_pb2.Reply(message="SQUIIIK SQUIIIK COUIC!")


def serve():
    port = random.randint(50000, 50100)
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    mouse_pb2_grpc.add_MouseServiceServicer_to_server(MouseServiceServicer(), server)

    server.add_insecure_port(f"[::]:{port}")
    print(f"[Mouse] Service lancé sur le port {port}")
    server.start()

    server.wait_for_termination()


if __name__ == "__main__":
    serve()
