#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import random
import logging
import subprocess
import json
from typing import Optional, Tuple
from urllib.parse import urlparse
from pathlib import Path

class CloudImageProcessor:
    def __init__(self):
        self.setup_logging()
        self.vm_storage = "/var/lib/vz/template/iso"  # Armazenamento padrão do Proxmox
        self.images_dir = "/root/imagens"  # Diretório para armazenar imagens
        self.ensure_images_directory()
        
    def setup_logging(self):
        """Configurar logging para a aplicação."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def ensure_images_directory(self):
        """Criar diretório de imagens se não existir."""
        try:
            Path(self.images_dir).mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Diretório de imagens criado/verificado em {self.images_dir}")
        except Exception as e:
            self.logger.error(f"Falha ao criar diretório de imagens: {str(e)}")
            raise

    def validate_url(self, url: str) -> bool:
        """Validar se a URL é válida e aponta para um arquivo de imagem."""
        try:
            result = urlparse(url)
            valid_extensions = ('.img', '.qcow2')
            return all([result.scheme, result.netloc]) and url.lower().endswith(valid_extensions)
        except Exception:
            return False

    def get_available_storages(self) -> list:
        """Obter lista de storages disponíveis no Proxmox."""
        try:
            result = subprocess.run("pvesm status", shell=True, check=True, text=True,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            # Pular a primeira linha (cabeçalho) e processar as demais
            storages = []
            for line in result.stdout.strip().split('\n')[1:]:
                if line.strip():
                    storage = line.split()[0]
                    storages.append(storage)
            return storages
        except Exception as e:
            self.logger.error(f"Erro ao obter storages: {str(e)}")
            return []

    def run_command(self, command: str) -> Tuple[bool, str]:
        """Executar comando do sistema e tratar erros."""
        try:
            self.logger.info(f"Executando comando: {command}")
            result = subprocess.run(command, shell=True, check=True, text=True,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Falha no comando: {e.stderr}")
            return False, e.stderr
        except Exception as e:
            self.logger.error(f"Erro ao executar comando: {str(e)}")
            return False, str(e)

    def wait_for_disk_import(self, vm_id: int, storage: str, volume_name: str, max_attempts: int = 30) -> bool:
        """Aguardar até que o disco seja importado corretamente."""
        self.logger.info("Aguardando a importação do disco ser concluída...")
        
        # O Proxmox adiciona o prefixo vm-[ID]-disk- ao nome do volume
        expected_volume = f"vm-{vm_id}-disk-0"
        
        for attempt in range(max_attempts):
            # Verificar se o volume existe no storage
            success, output = self.run_command(f"pvesm list {storage}")
            if success and expected_volume in output:
                self.logger.info("Disco importado com sucesso")
                return True
                
            time.sleep(1)  # Aguardar 1 segundo antes da próxima verificação
            self.logger.info(f"Tentativa {attempt + 1}/{max_attempts} - Aguardando importação do disco...")
            
        self.logger.error("Tempo limite excedido aguardando a importação do disco")
        return False

    def create_cloud_init_config(self, vm_id: int) -> str:
        """Criar configuração cloud-init para a VM."""
        config = {
            "user": "root",
            "password": "your-password-here",
            "chpasswd": {"expire": False},
            "ssh_pwauth": True,
            "disable_root": False,
            "ssh_authorized_keys": [],
            "package_upgrade": True,
            "packages": ["qemu-guest-agent"],
            "runcmd": [
                "systemctl enable qemu-guest-agent",
                "systemctl start qemu-guest-agent"
            ]
        }
        
        config_path = os.path.join(self.images_dir, f"cloud-init-{vm_id}.yaml")
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        return config_path

    def check_image_exists(self, image_path: str) -> bool:
        """Verificar se a imagem já existe no diretório."""
        return os.path.exists(image_path) and os.path.getsize(image_path) > 0

    def process_cloud_image(self, cloud_img_url: str, storage: str) -> bool:
        """Processar imagem cloud e preparar para o Proxmox."""
        if not self.validate_url(cloud_img_url):
            self.logger.error("URL fornecida é inválida")
            return False

        try:
            # Gerar ID aleatório da VM entre 1030 e 1040
            vm_id = random.randint(1030, 1040)
            image_name = cloud_img_url.split("/")[-1]
            # Remover extensão do arquivo para usar como nome do volume
            volume_name = os.path.splitext(image_name)[0]
            final_image_name = f"{volume_name}.qcow2"
            
            # Definir caminhos completos para as imagens
            temp_image_path = os.path.join(self.images_dir, image_name)
            final_image_path = os.path.join(self.images_dir, final_image_name)
            
            # Verificar se a imagem já existe
            if self.check_image_exists(temp_image_path):
                self.logger.info(f"Imagem {image_name} já existe em {self.images_dir}, pulando download")
            else:
                # Baixar a imagem
                self.logger.info(f"Baixando {image_name} para {self.images_dir}")
                success, _ = self.run_command(f"wget {cloud_img_url} -O {temp_image_path}")
                if not success:
                    return False

            # Converter imagem para formato qcow2 mantendo o tamanho original
            self.logger.info("Convertendo imagem para formato qcow2")
            success, _ = self.run_command(f"qemu-img convert -O qcow2 {temp_image_path} {final_image_path}")
            if not success:
                return False

            # Criar configuração cloud-init
            config_path = self.create_cloud_init_config(vm_id)

            # Criar VM no Proxmox
            success, _ = self.run_command(
                f"qm create {vm_id} --memory 2048 --cores 2 --name {volume_name} --net0 virtio,bridge=vmbr0 --machine q35 --scsihw virtio-scsi-single"
            )
            if not success:
                return False

            # Importar disco
            self.logger.info("Importando disco...")
            success, _ = self.run_command(f"qm importdisk {vm_id} {final_image_path} {storage} --format qcow2")
            if not success:
                return False

            # Aguardar a importação do disco ser concluída
            if not self.wait_for_disk_import(vm_id, storage, volume_name):
                return False

            # Configurar definições da VM
            vm_configs = [
                f"qm set {vm_id} --scsihw virtio-scsi-pci --scsi0 {storage}:vm-{vm_id}-disk-0",
                f"qm set {vm_id} --ide2 {storage}:cloudinit",
                f"qm set {vm_id} --boot c --bootdisk scsi0",
                f"qm set {vm_id} --serial0 socket --vga serial0",
                f"qm set {vm_id} --agent enabled=1"
            ]

            for config_cmd in vm_configs:
                success, _ = self.run_command(config_cmd)
                if not success:
                    return False

            # Limpar arquivos temporários
            self.logger.info("Limpando arquivos temporários...")
            self.run_command(f"rm -f {temp_image_path} {final_image_path} {config_path}")

            self.logger.info(f"Template da VM {vm_id} criado com sucesso")
            return True

        except Exception as e:
            self.logger.error(f"Erro ao processar imagem cloud: {str(e)}")
            return False

def main():
    processor = CloudImageProcessor()
    
    print("\nProcessador de Templates Cloud para Proxmox")
    print("==========================================")
    print("\nEste script irá baixar e configurar uma imagem cloud para uso no Proxmox 8.0")
    print(f"\nAs imagens serão armazenadas em: /root/imagens")
    
    # Obter e mostrar storages disponíveis
    storages = processor.get_available_storages()
    if not storages:
        print("\nErro: Não foi possível obter a lista de storages disponíveis.")
        return
    
    print("\nStorages disponíveis:")
    for i, storage in enumerate(storages, 1):
        print(f"{i}. {storage}")
    
    while True:
        try:
            storage_index = int(input("\nEscolha o número do storage para o template (ou 0 para sair): ")) - 1
            if storage_index == -1:
                break
            if 0 <= storage_index < len(storages):
                selected_storage = storages[storage_index]
                break
            print("Opção inválida. Por favor, escolha um número válido.")
        except ValueError:
            print("Por favor, digite um número válido.")
    
    if storage_index == -1:
        return
    
    while True:
        cloud_img_url = input("\nDigite a URL da imagem cloud (ou 'q' para sair): ").strip()
        
        if cloud_img_url.lower() == 'q':
            break
            
        if processor.process_cloud_image(cloud_img_url, selected_storage):
            print("\nProcessamento da imagem concluído com sucesso!")
        else:
            print("\nFalha ao processar a imagem. Verifique os logs para mais detalhes.")

if __name__ == "__main__":
    main()
