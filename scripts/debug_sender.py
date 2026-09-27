#!/usr/bin/env python3
"""Debug del sender identity en SendGrid."""
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

print('=== VERIFICANDO QUE EL PAYLOAD LLEGA CORRECTO ===')
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

print('Payload que se enviará:')
import json
print(json.dumps(payload, indent=2))
print()

# Enviar con el payload
print('=== ENVIANDO SOLICITUD ===')
r = httpx.post('https://api.sendgrid.com/v3/senders', headers=headers, json=payload, timeout=10.0)
print('Status:', r.status_code)
print('Respuesta:', r.text[:500])
print()

# Ver qué está en la respuesta
if r.status_code == 201:
    data = r.json()
    print('Sender creado:')
    print('  email:', data.get('email'))
    print('  from.email:', data.get('from', {}).get('email'))
    print('  verified:', data.get('verified'))
    print()
    
    # Verificar con GET
    sender_id = data.get('id')
    if sender_id:
        print(f'=== VERIFICANDO CON GET /v3/senders/{sender_id} ===')
        r2 = httpx.get(f'https://api.sendgrid.com/v3/senders/{sender_id}', headers=headers, timeout=10.0)
        print('Status:', r2.status_code)
        if r2.status_code == 200:
            data2 = r2.json()
            print('  email:', data2.get('email'))
            print('  from.email:', data2.get('from', {}).get('email'))
            print('  verified:', data2.get('verified'))
            print('  id:', data2.get('id'))
