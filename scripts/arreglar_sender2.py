#!/usr/bin/env python3
"""Limpiar y crear sender identity en SendGrid."""
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

print('=== PASO 1: Eliminar sender con email None ===')
r = httpx.get('https://api.sendgrid.com/v3/senders', headers=headers, timeout=10.0)
senders = r.json() if isinstance(r.json(), list) else r.json().get('result', [])
print(f'Senders: {len(senders)}')
for s in senders:
    print(f"  - id={s.get('id')} email={s.get('email')} verified={s.get('verified')}")

sender_a_eliminar = None
for s in senders:
    if s.get('email') is None:
        sender_a_eliminar = s
        break

if sender_a_eliminar:
    sender_id = sender_a_eliminar.get('id')
    print()
    print(f'Eliminando sender id={sender_id}...')
    r2 = httpx.delete(f'https://api.sendgrid.com/v3/senders/{sender_id}', headers=headers, timeout=10.0)
    print('Status:', r2.status_code)
    print('Eliminado:', r2.status_code == 204)
else:
    print()
    print('No hay sender con email None para eliminar')

print()
print('=== PASO 2: Eliminar sender con nickname duplicado ===')
r3 = httpx.get('https://api.sendgrid.com/v3/senders', headers=headers, timeout=10.0)
senders2 = r3.json() if isinstance(r3.json(), list) else r3.json().get('result', [])
for s in senders2:
    if s.get('nickname') == 'SMIP' and s.get('email') is not None:
        print(f'  Sender duplicado encontrado: id={s.get("id")} email={s.get("email")}')
        r4 = httpx.delete(f'https://api.sendgrid.com/v3/senders/{s.get("id")}', headers=headers, timeout=10.0)
        print(f'  Eliminado: status={r4.status_code}')

print()
print('=== PASO 3: Crear sender con email verificado ===')
payload = {
    'name': 'SMIP',
    'nickname': 'SMIP-2024',
    'email': 'leaonzar1234@gmail.com',
    'from': {
        'email': 'leaonzar1234@gmail.com',
        'name': 'SMIP'
    }
}

print('Payload:', payload)
r5 = httpx.post('https://api.sendgrid.com/v3/senders', headers=headers, json=payload, timeout=10.0)
print('Status:', r5.status_code)
print('Respuesta:', r5.text[:500])

if r5.status_code == 201:
    sender_data = r5.json()
    print()
    print('✅ Sender creado!')
    print(f'   id: {sender_data.get("id")}')
    print(f'   email: {sender_data.get("email")}')
    print(f'   verified: {sender_data.get("verified")}')
    
    # Verificar con GET
    if sender_data.get('id'):
        print()
        print(f'=== VERIFICANDO CON GET /v3/senders/{sender_data.get("id")} ===')
        r6 = httpx.get(f'https://api.sendgrid.com/v3/senders/{sender_data.get("id")}', headers=headers, timeout=10.0)
        print('Status:', r6.status_code)
        if r6.status_code == 200:
            data2 = r6.json()
            print(f'  email: {data2.get("email")}')
            print(f'  verified: {data2.get("verified")}')
