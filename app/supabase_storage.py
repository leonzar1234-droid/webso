"""
Integración con Supabase Storage para persistencia de archivos.
Los archivos se almacenan en el bucket de Supabase Storage.
"""

import os
from typing import Any

from supabase import Client, create_client


# variables de entorno
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")


def get_supabase_client() -> Client:
    """Retorna el cliente de Supabase configurado."""
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise EnvironmentError(
            "SUPABASE_URL y SUPABASE_ANON_KEY deben estar configuradas en las variables de entorno"
        )
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


def upload_file(file_content: bytes, filename: str) -> dict[str, Any]:
    """
    Sube un archivo a Supabase Storage.
    Retorna info del archivo subido.
    """
    client = get_supabase_client()
    bucket_name = "tkkrpzgzjquyxghpjzhm"  # nombre del bucket (project id)
    
    # Subir al bucket
    response = client.storage.from_(bucket_name).upload(
        file_content,
        filename,
        file_options={"content-type": "application/octet-stream"}
    )
    
    # Obtener URL pública
    public_url = client.storage.from_(bucket_name).get_public_url(filename)
    
    return {
        "filename": filename,
        "size": len(file_content),
        "download_url": public_url,
        "path": filename,
    }


def list_files() -> list[dict[str, Any]]:
    """Lista todos los archivos en el bucket de Supabase Storage."""
    client = get_supabase_client()
    bucket_name = "tkkrpzgzjquyxghpjzhm"
    
    try:
        response = client.storage.from_(bucket_name).list()
        
        files = []
        for item in response:
            public_url = client.storage.from_(bucket_name).get_public_url(item["name"])
            
            # Extraer solo el nombre del archivo
            file_name = item["name"].split("/")[-1] if "/" in item["name"] else item["name"]
            
            files.append({
                "filename": file_name,
                "name": file_name,
                "size": item.get("size", 0),
                "download_url": public_url,
                "path": item["name"],
            })
        
        return files
    except Exception as e:
        print(f"Error al listar archivos: {e}")
        return []


def download_file(filename: str) -> bytes:
    """Descarga un archivo específico desde Supabase Storage."""
    client = get_supabase_client()
    bucket_name = "tkkrpzgzjquyxghpjzhm"
    
    try:
        file_content = client.storage.from_(bucket_name).download(filename)
        return file_content
    except Exception as e:
        print(f"Error al descargar archivo '{filename}': {e}")
        raise FileNotFoundError(f"Archivo '{filename}' no encontrado")


def delete_file(filename: str) -> bool:
    """Elimina un archivo del bucket de Supabase Storage."""
    client = get_supabase_client()
    bucket_name = "tkkrpzgzjquyxghpjzhm"
    
    try:
        client.storage.from_(bucket_name).remove([filename])
        return True
    except Exception as e:
        print(f"Error al eliminar archivo '{filename}': {e}")
        return False
