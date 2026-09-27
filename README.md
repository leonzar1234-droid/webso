# SMIP

Aplicación web académica desarrollada con FastAPI.

## Funcionalidades

- **Carga de archivos** (upload): el navegador envía archivos al servidor.
- **Descarga de archivos** (download): el servidor entrega archivos almacenados.
- **Envío de correos** (email): envío de mensajes electrónicos vía SMTP.

## Tecnologías

- Python 3.12
- FastAPI
- Uvicorn
- HTML / CSS / JavaScript

## Estructura

```
SMIP/
├── .venv/              # Entorno virtual (ya creado)
├── app/
│   ├── __init__.py
│   ├── main.py         # Punto de entrada de FastAPI
│   ├── templates/
│   │   └── index.html  # Página principal
│   └── static/
│       ├── style.css   # Estilos
│       └── script.js   # Comportamiento cliente
├── uploads/            # Archivos subidos (vacío inicialmente)
├── requirements.txt
├── .gitignore
└── README.md
```

## Ciclo de desarrollo

Este proyecto se construye por fases. Actualmente se encuentra en la **Fase 1**:
- Estructura inicial configurada.
- FastAPI + Uvicorn operativos.
- Interfaz web básica funcional.
- *Pendiente*: subida, descarga y correo.

## Ejecución local

```bash
# Activar entorno virtual
.\.venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar servidor
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

La aplicación estará disponible en `http://127.0.0.1:8000`.

## Estado

| Fase | Descripción | Estado |
|------|-------------|--------|
| 1 | Estructura inicial + FastAPI básico + interfaz | ✅ Completada |
| 2 | Subida de archivos | 🔲 Pendiente |
| 3 | Descarga de archivos | 🔲 Pendiente |
| 4 | Envío de correos SMTP | 🔲 Pendiente |
| 5 | Publicación | 🔲 Pendiente |

## Notas

- Este proyecto es académico.
- No se han configurado servicios externos ni se ha publicado en Internet.
- Se usa el entorno virtual `.venv` ya existente en el directorio raíz.
