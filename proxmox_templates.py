# -*- coding: utf-8 -*-
import os
import random
import time

#para funcionar deve instalar o pacote: libguestfs-tools com o comando apt-get install libguestfs-tools no nó proxmox 

imagens = [ "https://cloud-images.ubuntu.com/bionic/current/bionic-server-cloudimg-amd64.img",
"https://cloud-images.ubuntu.com/focal/current/focal-server-cloudimg-amd64-disk-kvm.img",
"https://cloud-images.ubuntu.com/minimal/releases/focal/release/ubuntu-20.04-minimal-cloudimg-amd64.img",
"https://cloud-images.ubuntu.com/daily/server/groovy/current/groovy-server-cloudimg-amd64-disk-kvm.img",
"https://cloud-images.ubuntu.com/hirsute/current/hirsute-server-cloudimg-amd64.img",
"https://cdimage.debian.org/cdimage/openstack/current-10/debian-10-openstack-amd64.qcow2",
"https://cdimage.debian.org/cdimage/openstack/current-9/debian-9-openstack-amd64.qcow2",
"http://cloud.centos.org/centos/7/images/CentOS-7-x86_64-GenericCloud.qcow2",
"https://cloud.centos.org/centos/8/x86_64/images/CentOS-8-GenericCloud-8.2.2004-20200611.2.x86_64.qcow2",
"https://cloud.centos.org/centos/8-stream/x86_64/images/CentOS-Stream-GenericCloud-8-20210210.0.x86_64.qcow2",
"https://download.fedoraproject.org/pub/fedora/linux/releases/32/Cloud/x86_64/images/Fedora-Cloud-Base-32-1.6.x86_64.qcow2",
"https://github.com/rancher/os/releases/download/v1.5.5/rancheros-openstack.img",
"https://mirror.pkgbuild.com/images/v20210315.17387/Arch-Linux-x86_64-cloudimg-20210315.17387.qcow2",
"https://repo.almalinux.org/almalinux/8/cloud/x86_64/images/AlmaLinux-8-GenericCloud-latest.x86_64.qcow2",
"https://mirror.pkgbuild.com/images/v20210315.17387/Arch-Linux-x86_64-cloudimg-20210315.17387.qcow2",
]

os.system("export EDITOR=nano") #definindo o editor nano. Não mude se não funciona
#os.system("export LIBGUESTFS_DEBUG=1") # so ativer em caso de debug
#os.system("export LIBGUESTFS_TRACE=1")  # so ativer em caso de debug

#laço de repetição para editar as aimagems com virt-edit
for cloud_img_url in imagens:
    vm_id=random.randint(1012,1032)
    image_name=cloud_img_url.split("/")[-1] #split para pegar o nome do arquivo
    os.system("echo 'Baixando {}'".format(image_name))
    os.system("wget {}".format(cloud_img_url))
    os.system("echo 'Editando: {}'".format(image_name))
    os.system("virt-edit -a {} /etc/cloud/cloud.cfg -e 's/disable_root: [Tt]rue/disable_root: False/'".format(image_name))
    os.system("virt-edit -a {} /etc/cloud/cloud.cfg -e 's/disable_root: 1/disable_root: 0/'".format(image_name))
    os.system("virt-edit -a {} /etc/cloud/cloud.cfg -e 's/ssh_pwauth:   0/ssh_pwauth:   1/'".format(image_name))
    os.system("virt-edit -a {} /etc/cloud/cloud.cfg -e 's/lock_passwd: [Tt]rue/lock_passwd: False/'".format(image_name))
    os.system("virt-edit -a {} /etc/cloud/cloud.cfg -e 's/lock_passwd: 1/lock_passwd: 0/'".format(image_name))
    os.system("virt-edit -a {} /etc/ssh/sshd_config -e 's/PasswordAuthentication no/PasswordAuthentication yes/'".format(image_name))
    os.system("virt-edit -a {} /etc/ssh/sshd_config -e 's/#PermitRootLogin [Yy]es/PermitRootLogin yes/'".format(image_name))
    os.system("virt-edit -a {} /etc/ssh/sshd_config -e 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/'".format(image_name))
    os.system("virt-edit -a {} /etc/ssh/sshd_config -e 's/#MaxAuthTries 6/MaxAuthTries 20/'".format(image_name))
    os.system("virt-customize --install iotop,iftop,htop,nano,vim,qemu-guest-agent,curl,wget -a {}".format(image_name))
    time.sleep(30) #tempo de espera da instalações dos pacote
    #os.system("mv {} /var/lib/vz/template/qemu/{}".format(image_name,image_name)) ver se é necessário
    os.system("echo 'Criando o template: {}'".format(image_name))
    os.system("qm create {} --memory 512 --net0 virtio,bridge=vmbr2,firewall=0".format(vm_id))
    os.system("qm importdisk {} {} local".format(vm_id,image_name))
    os.system("qm set {} --ide0 local:cloudinit".format(vm_id))
    os.system("qm set {} --boot c --bootdisk scsi0".format(vm_id))
    os.system("qm set {} --serial0 socket --vga serial0".format(vm_id))



print("Finalizado! Os templates se encontra no nó proxmox")