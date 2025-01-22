#!/bin/bash
docker buildx create --use --name py3-builder --node py3-builder0 --driver docker-container --driver-opt image=moby/buildkit:v0.10.6
docker buildx build --platform linux/amd64,linux/arm64 --tag opensourcebssd/service-ocr:latest . --push

