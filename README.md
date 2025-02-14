# Implementación de Algoritmo de Consenso para Elección de Líder

Este proyecto es una implementación de un algoritmo de consenso para la elección de un líder. El sistema está compuesto por varios componentes distribuidos que interactúan entre sí utilizando gRPC y Protobuf. Los componentes principales son dos seguidores (followers), un líder, un proxy y un cliente. Cada componente se despliega en una instancia separada de AWS, y cada instancia ejecuta su código correspondiente en un puerto específico.

## Descripción General

El sistema permite la lectura y escritura en una base de datos distribuida, donde se sigue el siguiente flujo de ejecución:
1. Se ejecutan primero los dos seguidores (followers).
2. Luego, se ejecuta el líder.
3. Después, se corre el proxy.
4. Finalmente, se inicia el cliente.

Desde el cliente, es posible escribir en la base de datos y leer de ella. Además, se puede simular la caída del cliente con `Ctrl + C`, lo que termina la ejecución del programa y simula una interrupción en la comunicación.

## Requisitos

Para configurar las instancias en AWS, se realizaron los siguientes pasos de instalación en cada instancia:

### Actualización de la instancia:
```bash
sudo apt update && sudo apt upgrade -y
```

### Instalación de Python y pip:
```bash
sudo apt install python3 python3-pip -y
```

### Verificación de versiones:
```bash
python3 --version
pip3 --version
```

### Instalación de `venv` y pip completo:
```bash
sudo apt install python3-venv python3-pip -y
```

### Creación de un entorno virtual:
```bash
python3 -m venv leader-env
```

### Activación del entorno virtual:
```bash
source leader-env/bin/activate
```

### Instalación de gRPC y Protobuf en el entorno virtual:
```bash
pip install grpcio grpcio-tools
```

## Ejecución del Sistema

Para iniciar el sistema, los archivos Python deben ejecutarse en el siguiente orden:

1. Ejecuta los seguidores (followers):
   ```bash
   python3 follower1.py
   python3 follower2.py
   ```

2. Ejecuta el líder:
   ```bash
   python3 leader.py
   ```

3. Ejecuta el proxy:
   ```bash
   python3 proxy.py
   ```

4. Ejecuta el cliente:
   ```bash
   python3 client.py
   ```

## Interacción con el Sistema

El cliente permite realizar operaciones de lectura y escritura en la base de datos distribuida. Para simular la caída del cliente, se puede utilizar la combinación de teclas `Ctrl + C`, lo cual termina el proceso de ejecución y desconecta el cliente del sistema.

## Notas adicionales

- Asegúrate de activar el entorno virtual en cada instancia antes de ejecutar los scripts.
- El uso de gRPC y Protobuf requiere que se compilen los archivos `.proto` correspondientes, los cuales están incluidos en el repositorio.

