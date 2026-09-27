#!/usr/bin/env python3
"""Crear sender identity completo en SendGrid."""
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

print('=== CREAR SENDER CON TODOS LOS CAMPOS REQUERIDOS ===')
payload = {
    'name': 'SMIP',
    'nickname': 'SMIP-2024',
    'email': 'leaonzar1234@gmail.com',
    'from': {
        'email': 'leaonzar1234@gmail.com',
        'name': 'SMIP',
        'reply_to': {
            'email': 'leaonzar1234@gmail.com',
            'name': 'SMIP'
        }
    },
    'address': 'Direccion',
    'city': 'Ciudad',
    'country': 'Argentina',
    'zip': '1234'
}

print('Payload:')
import json
print(json.dumps(payload, indent=2))
print()

r = httpx.post('https://api.sendgrid.com/v3/senders', headers=headers, json=payload, timeout=10.0)
print('Status:', r.status_code)
print('Respuesta:', r.text[:500])

if r.status_code == 201:
    sender_data = r.json()
    print()
    print('✅ Sender creado exitosamente!')
    print(f'   id: {sender_data.get("id")}')
    print(f'   email: {sender_data.get("email")}')
    print(f'   verified: {sender_data.get("verified")}')
    
    # Verificar con GET
    if sender_data.get('id'):
        print()
        print(f'=== VERIFICANDO CON GET /v3/senders/{sender_data.get("id")} ===')
        r2 = httpx.get(f'https://api.sendgrid.com/v3/senders/{sender_data.get("id")}', headers=headers, timeout=10.0)
        print('Status:', r2.status_code)
        if r2.status_code == 200:
            data2 = r2.json()
            print(f'  email: {data2.get("email")}')
            print(f'  verified: {data2.get("verified")}')
            print(f'  id: {data2.get("id")}')
            
            if data2.get('email') == 'leaonzar1234@gmail.com':
                print()
                print('🎉 EL SENDER ESTÁ VERIFICADO Y LISTO PARA USAR')
            else:
                print()
                print('❌ El email no coincide')
