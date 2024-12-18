#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import random
import logging
import subprocess
import json
from typing import Optional
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

    def run_command(self, command: str) -> bool:
        """Executar comando do sistema e tratar erros."""
        try:
            self.logger.info(f"Executando comando: {command}")
            result = subprocess.run(command, shell=True, check=True, text=True,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Falha no comando: {e.stderr}")
            return False
        except Exception as e:
            self.logger.error(f"Erro ao executar comando: {str(e)}")
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

    def process_cloud_image(self, cloud_img_url: str) -> bool:
        """Processar imagem cloud e preparar para o Proxmox."""
        if not self.validate_url(cloud_img_url):
            self.logger.error("URL fornecida é inválida")
            return False

        try:
            # Gerar ID aleatório da VM entre 1030 e 1040
            vm_id = random.randint(1030, 1040)
            image_name = cloud_img_url.split("/")[-1]
            final_image_name = f"vm-{vm_id}-disk-0.qcow2"
            
            # Definir caminhos completos para as imagens
            temp_image_path = os.path.join(self.images_dir, image_name)
            final_image_path = os.path.join(self.images_dir, final_image_name)
            
            # Verificar se a imagem já existe
            if self.check_image_exists(temp_image_path):
                self.logger.info(f"Imagem {image_name} já existe em {self.images_dir}, pulando download")
            else:
                # Baixar a imagem
                self.logger.info(f"Baixando {image_name} para {self.images_dir}")
                if not self.run_command(f"wget {cloud_img_url} -O {temp_image_path}"):
                    return False

            # Converter e redimensionar a imagem para 32G
            self.logger.info("Convertendo e redimensionando imagem")
            if not self.run_command(f"qemu-img convert -O qcow2 {temp_image_path} {final_image_path}"):
                return False
            
            if not self.run_command(f"qemu-img resize {final_image_path} 32G"):
                return False

            # Criar configuração cloud-init
            config_path = self.create_cloud_init_config(vm_id)

            # Criar VM no Proxmox
            commands = [
                # Criar VM
                f"qm create {vm_id} --memory 2048 --cores 2 --name cloud-init-{vm_id} --net0 virtio,bridge=vmbr0",
                
                # Importar disco
                f"qm importdisk {vm_id} {final_image_path} local",
                
                # Configurar definições da VM
                f"qm set {vm_id} --scsihw virtio-scsi-pci --scsi0 local:vm-{vm_id}-disk-0",
                f"qm set {vm_id} --ide2 local:cloudinit",
                f"qm set {vm_id} --boot c --bootdisk scsi0",
                f"qm set {vm_id} --serial0 socket --vga serial0",
                f"qm set {vm_id} --agent enabled=1",
                
                # Limpar arquivos temporários
                f"rm -f {temp_image_path} {final_image_path} {config_path}"
            ]

            for command in commands:
                if not self.run_command(command):
                    self.logger.error(f"Falha ao executar comando: {command}")
                    return False

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
    
    while True:
        cloud_img_url = input("\nDigite a URL da imagem cloud (ou 'q' para sair): ").strip()
        
        if cloud_img_url.lower() == 'q':
            break
            
        if processor.process_cloud_image(cloud_img_url):
            print("\nProcessamento da imagem concluído com sucesso!")
        else:
            print("\nFalha ao processar a imagem. Verifique os logs para mais detalhes.")

if __name__ == "__main__":
    main()
