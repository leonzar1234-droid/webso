#!/usr/bin/env python3
"""Arreglar sender identity en SendGrid."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

api_key = os.environ.get('SENDGRID_API_KEY')
print('API Key:', api_key[:10] if api_key else 'NO')
print()

import httpx
headers = {
    'Authorization': f'Bearer {api_key}',
    'Content-Type': 'application/json'
}

print('=== PASO 1: Buscar sender con email None ===')
r = httpx.get('https://api.sendgrid.com/v3/senders', headers=headers, timeout=10.0)
print('Status:', r.status_code)
senders = r.json() if isinstance(r.json(), list) else r.json().get('result', [])
print(f'Senders: {len(senders)}')
for s in senders:
    print(f"  - id={s.get('id')} email={s.get('email')} verified={s.get('verified')}")

# Buscar el sender con email None
sender_a_eliminar = None
for s in senders:
    if s.get('email') is None:
        sender_a_eliminar = s
        break

if sender_a_eliminar:
    print()
    print('=== PASO 2: Eliminar sender con email None ===')
    sender_id = sender_a_eliminar.get('id')
    r2 = httpx.delete(f'https://api.sendgrid.com/v3/senders/{sender_id}', headers=headers, timeout=10.0)
    print('Status:', r2.status_code)
    print('Respuesta:', r2.text[:200])
else:
    print()
    print('No hay sender con email None para eliminar')

print()
print('=== PASO 3: Crear sender con email verificado ===')
payload = {
    'name': 'SMIP',
    'nickname': 'SMIP',
    'email': 'leaonzar1234@gmail.com',
    'from': {
        'email': 'leaonzar1234@gmail.com',
        'name': 'SMIP',
        'reply_to': {
            'email': 'leaonzar1234@gmail.com',
            'name': 'SMIP'
        }
    },
    'address': 'Casa',
    'city': 'Ciudad',
    'country': 'Argentina',
    'zip': '1234'
}

r3 = httpx.post('https://api.sendgrid.com/v3/senders', headers=headers, json=payload, timeout=10.0)
print('Status:', r3.status_code)
print('Respuesta:', r3.text[:500])

if r3.status_code == 201:
    sender_data = r3.json()
    print()
    print('✅ Sender creado!')
    print(f'   id: {sender_data.get("id")}')
    print(f'   email: {sender_data.get("email")}')
    print(f'   verified: {sender_data.get("verified")}')
    
    # Verificar que se creó correctamente
    print()
    print('=== PASO 4: Verificar que el sender está correcto ===')
    r4 = httpx.get(f'https://api.sendgrid.com/v3/senders/{sender_data.get("id")}', headers=headers, timeout=10.0)
    print('Status:', r4.status_code)
    if r4.status_code == 200:
        data = r4.json()
        print(f'Sender verificado:')
        print(f'  email: {data.get("email")}')
        print(f'  verified: {data.get("verified")}')
else:
    print()
    print('❌ No se pudo crear el sender')
    print('Posibles causas:')
    print('1. El correo ya está verificado en otro sender')
    print('2. Error en los datos del payload')
    print('3. API Key sin permisos suficientes')
