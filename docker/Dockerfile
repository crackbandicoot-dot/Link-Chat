# Dockerfile para Link-Chat
FROM python:3.9-slim

# Instalar dependencias del sistema necesarias para raw sockets
RUN apt-get update && apt-get install -y \
    net-tools \
    iputils-ping \
    iproute2 \
    tcpdump \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Crear usuario para la aplicación
RUN useradd -m -s /bin/bash linkchat && \
    echo "linkchat ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Establecer directorio de trabajo
WORKDIR /app

# Copiar archivos de la aplicación
COPY . .

# Cambiar propietario de los archivos
RUN chown -R linkchat:linkchat /app

# Cambiar al usuario linkchat
USER linkchat

# Crear directorio para archivos recibidos
RUN mkdir -p /app/received_files

# Exponer información del contenedor
LABEL maintainer="Link-Chat Team"
LABEL description="Link-Chat - Data Link Layer Messaging Application"
LABEL version="1.0"

# Comando por defecto - mantener contenedor corriendo para terminales interactivas
CMD ["tail", "-f", "/dev/null"]
