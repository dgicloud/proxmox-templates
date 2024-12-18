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
        self.vm_storage = "/var/lib/vz/template/iso"  # Default Proxmox template storage
        
    def setup_logging(self):
        """Configure logging for the application."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def validate_url(self, url: str) -> bool:
        """Validate if the provided URL is valid and points to an image file."""
        try:
            result = urlparse(url)
            valid_extensions = ('.img', '.qcow2')
            return all([result.scheme, result.netloc]) and url.lower().endswith(valid_extensions)
        except Exception:
            return False

    def run_command(self, command: str) -> bool:
        """Execute a system command and handle errors."""
        try:
            self.logger.info(f"Executing: {command}")
            result = subprocess.run(command, shell=True, check=True, text=True,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Command failed: {e.stderr}")
            return False
        except Exception as e:
            self.logger.error(f"Error executing command: {str(e)}")
            return False

    def create_cloud_init_config(self, vm_id: int) -> str:
        """Create cloud-init configuration for the VM."""
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
        
        config_path = f"/tmp/cloud-init-{vm_id}.yaml"
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        return config_path

    def process_cloud_image(self, cloud_img_url: str) -> bool:
        """Process a cloud image and prepare it for Proxmox."""
        if not self.validate_url(cloud_img_url):
            self.logger.error("Invalid URL provided")
            return False

        try:
            # Generate random VM ID between 1030 and 1040
            vm_id = random.randint(1030, 1040)
            image_name = cloud_img_url.split("/")[-1]
            final_image_name = f"vm-{vm_id}-disk-0.qcow2"
            
            # Download the image
            self.logger.info(f"Downloading {image_name}")
            if not self.run_command(f"wget {cloud_img_url} -O /tmp/{image_name}"):
                return False

            # Convert and resize the image to 32G
            self.logger.info("Converting and resizing image")
            if not self.run_command(f"qemu-img convert -O qcow2 /tmp/{image_name} /tmp/{final_image_name}"):
                return False
            
            if not self.run_command(f"qemu-img resize /tmp/{final_image_name} 32G"):
                return False

            # Create cloud-init config
            config_path = self.create_cloud_init_config(vm_id)

            # Create Proxmox VM
            commands = [
                # Create VM
                f"qm create {vm_id} --memory 2048 --cores 2 --name cloud-init-{vm_id} --net0 virtio,bridge=vmbr0",
                
                # Import disk
                f"qm importdisk {vm_id} /tmp/{final_image_name} local-lvm",
                
                # Configure VM settings
                f"qm set {vm_id} --scsihw virtio-scsi-pci --scsi0 local-lvm:vm-{vm_id}-disk-0",
                f"qm set {vm_id} --ide2 local-lvm:cloudinit",
                f"qm set {vm_id} --boot c --bootdisk scsi0",
                f"qm set {vm_id} --serial0 socket --vga serial0",
                f"qm set {vm_id} --agent enabled=1",
                
                # Clean up temporary files
                f"rm -f /tmp/{image_name} /tmp/{final_image_name} {config_path}"
            ]

            for command in commands:
                if not self.run_command(command):
                    self.logger.error(f"Failed executing command: {command}")
                    return False

            self.logger.info(f"Successfully created template VM {vm_id}")
            return True

        except Exception as e:
            self.logger.error(f"Error processing cloud image: {str(e)}")
            return False

def main():
    processor = CloudImageProcessor()
    
    print("\nProxmox Cloud Image Template Processor")
    print("======================================")
    print("\nThis script will download and configure a cloud image for use with Proxmox 8.0")
    
    while True:
        cloud_img_url = input("\nEnter the cloud image URL (or 'q' to quit): ").strip()
        
        if cloud_img_url.lower() == 'q':
            break
            
        if processor.process_cloud_image(cloud_img_url):
            print("\nImage processing completed successfully!")
        else:
            print("\nFailed to process the image. Check the logs for details.")

if __name__ == "__main__":
    main()
