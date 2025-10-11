# Link-Chat Docker Setup

Este directorio contiene la configuración de Docker para ejecutar Link-Chat en contenedores.

## Inicio Rápido

### Iniciar nodos con terminales interactivas separadas:

```powershell
cd docker
.\start-nodes.ps1
```

Este script:
1. Construye las imágenes Docker
2. Inicia 3 contenedores en modo detached
3. Abre 3 terminales PowerShell separadas, una para cada nodo
4. Cada terminal tiene acceso interactivo a su contenedor

### Dentro de cada terminal:

Una vez que las terminales se abran, ejecuta en cada una:

```bash
sudo python main.py
```

### Detener todos los nodos:

```powershell
.\stop-nodes.ps1
```

O manualmente:
```powershell
docker-compose down
```

## Método Alternativo (Manual)

### 1. Construir e iniciar contenedores:

```powershell
docker-compose up -d
```

### 2. Abrir terminales separadas manualmente:

**Terminal 1 (Node 1):**
```powershell
docker exec -it linkchat-node1 bash
```

**Terminal 2 (Node 2):**
```powershell
docker exec -it linkchat-node2 bash
```

**Terminal 3 (Node 3):**
```powershell
docker exec -it linkchat-node3 bash
```

## Estructura de la Red

- **Red**: `linkchat-network` (172.20.0.0/16)
- **Node 1**: 172.20.0.10
- **Node 2**: 172.20.0.11
- **Node 3**: 172.20.0.12

## Comandos Útiles

### Ver logs de un nodo:
```powershell
docker-compose logs -f linkchat-node1
```

### Ver logs de todos los nodos:
```powershell
docker-compose logs -f
```

### Reiniciar un nodo:
```powershell
docker-compose restart linkchat-node1
```

### Ver estado de los contenedores:
```powershell
docker-compose ps
```

### Entrar a un contenedor (si ya está corriendo):
```powershell
docker exec -it linkchat-node1 bash
```

### Inspeccionar la red:
```powershell
docker network inspect docker_linkchat-network
```

### Ver MACs de los contenedores:
```bash
# Dentro del contenedor
ip link show eth0
ifconfig eth0
```

## Solución de Problemas

### Los contenedores no inician:
```powershell
# Ver logs detallados
docker-compose logs

# Reconstruir desde cero
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

### Permisos insuficientes:
Los contenedores tienen `privileged: true` y `cap_add: NET_ADMIN, NET_RAW` para permitir raw sockets.

### No puedo ejecutar python:
Dentro del contenedor, usa:
```bash
sudo python main.py
```

## Archivos Compartidos

Los archivos en `docker/shared/` son accesibles desde todos los contenedores en `/app/shared/`.

Los archivos recibidos se guardan en volúmenes persistentes:
- Node 1: `node1-files`
- Node 2: `node2-files`
- Node 3: `node3-files`
