# Proxmox Template Creator

Script para criar templates de VMs no Proxmox a partir de imagens cloud.

## ⚠️ Aviso Importante

O arquivo `proxmox_templates.py` está **obsoleto** e não deve ser usado. Use o `main.py` que contém a versão mais recente e otimizada do script.

## 📋 Requisitos

- Proxmox VE 8.0 ou superior
- Python 3.6+
- Acesso root ao servidor Proxmox
- Conexão à internet para download das imagens

## 🚀 Como Usar

1. **Preparação**:
   ```bash
   # Crie o diretório para as imagens (se não existir)
   mkdir -p /root/imagens
   ```

2. **Execução**:
   ```bash
   python3 main.py
   ```

3. **Passos durante a execução**:
   - Escolha o storage onde o template será armazenado
   - Cole a URL da imagem cloud (formatos suportados: .img, .qcow2)
   - Aguarde a criação do template

## 🔍 Funcionalidades

- Download automático de imagens cloud
- Conversão para formato qcow2 (quando necessário)
- Criação de VM com configurações otimizadas:
  - Machine: q35
  - SCSI Controller: VirtIO SCSI single
  - Network: VirtIO
  - Cloud-init habilitado
  - QEMU Guest Agent configurado

## 🛠️ Configurações Padrão

- Memória: 2048MB
- CPUs: 2 cores
- Bridge de Rede: vmbr0
- IDs das VMs: 1030-1040 (aleatório)

## 📝 Exemplos de URLs de Imagens Cloud

- Ubuntu 20.04: `https://cloud-images.ubuntu.com/focal/current/focal-server-cloudimg-amd64.img`
- AlmaLinux 8: `https://repo.almalinux.org/almalinux/8/cloud/x86_64/images/AlmaLinux-8-GenericCloud-latest.x86_64.qcow2`
- Debian 11: `https://cloud.debian.org/images/cloud/bullseye/latest/debian-11-generic-amd64.qcow2`

## ⚙️ Cloud-Init

O template é configurado com as seguintes configurações cloud-init padrão:
- Usuário root habilitado
- Autenticação por senha SSH habilitada
- QEMU Guest Agent instalado e habilitado automaticamente

## 🤝 Contribuição

Sinta-se à vontade para abrir issues ou enviar pull requests com melhorias.

## 📜 Licença

Este projeto está sob a licença MIT.
