#!/usr/bin/env python3
"""Verificar si el correo está verificado en SendGrid."""
import os
import sys

# Forzar carga de .env
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

api_key = os.environ.get('SENDGRID_API_KEY')
print('API Key presente:', bool(api_key))
print('Primeros 10 chars:', api_key[:10] if api_key else 'NO')
print()

import httpx
headers = {
    'Authorization': f'Bearer {api_key}',
    'Content-Type': 'application/json'
}

print('=== VERIFICANDO SI EL CORREO ESTÁ VERIFICADO ===')
print('Buscando en /v3/senders...')
r = httpx.get('https://api.sendgrid.com/v3/senders', headers=headers, timeout=10.0)
print('Status:', r.status_code)

if r.status_code == 200:
    data = r.json()
    senders = data if isinstance(data, list) else data.get('result', [])
    print(f'Senders encontrados: {len(senders)}')
    for s in senders:
        print(f"  - {s.get('email')} (verified={s.get('verified')})")
    
    # Buscar el correo específico
    email_buscado = 'leaonzar1234@gmail.com'
    sender_encontrado = None
    for s in senders:
        if s.get('email') == email_buscado:
            sender_encontrado = s
            break
    
    if sender_encontrado:
        print()
        print(f'✅ CORREO ENCONTRADO: {sender_encontrado.get("email")}')
        print(f'   verified: {sender_encontrado.get("verified")}')
        print(f'   id: {sender_encontrado.get("id")}')
    else:
        print()
        print(f'❌ El correo {email_buscado} NO está en la lista de senders verificados')
else:
    print('Error:', r.text[:200])

print()
print('=== INTENTANDO VERIFICAR SI ES NECESARIO ===')
# Intentar crear el sender si no existe
if not sender_encontrado:
    payload = {
        'name': 'SMIP',
        'email': 'leaonzar1234@gmail.com'
    }
    print('Creando sender identity...')
    r2 = httpx.post('https://api.sendgrid.com/v3/senders', headers=headers, json=payload, timeout=10.0)
    print('Status:', r2.status_code)
    print('Respuesta:', r2.text[:300])
