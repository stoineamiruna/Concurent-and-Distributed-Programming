#!/usr/bin/env bash

openssl req -x509 \
    -newkey rsa:2048 \
    -keyout key.pem \
    -out cert.pem \
    -days 365 \
    -nodes \
    -subj "/CN=localhost" \
    -addext "subjectAltName=IP:127.0.0.1,DNS:localhost"

echo "done: cert.pem si key.pem generate"
