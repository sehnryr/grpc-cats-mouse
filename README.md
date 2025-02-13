# Cats & Mouse : GRPC

truc de cours de système distribué

## Usage

```bash
docker compose up
```

## Principes

La souris écoute sur un port random entre 50000 et 50100.
Les chats tentent de se connecter à la souris sur ces ports.

Dans cette implémentation, les chats se partagent les ports qu'ils ont essayé,
et choisissent un port aléatoire parmi ceux qui n'ont pas encore été essayés
pour tenter minimiser les risques les collisions.
