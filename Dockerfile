FROM python:3.13-slim

WORKDIR /app

# Copie du fichier des dépendances et installation
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie du code source
COPY . .

# Compilation des fichiers proto
RUN python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. cat.proto
RUN python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. mouse.proto

# Commande par défaut (surchargée via docker-compose)
CMD ["python"]
