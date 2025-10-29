#!/bin/bash
set -e

# Clean previous builds
echo "[*] Cleaning previous build artifacts..."
rm -f ./dynamic_build/output/*.so
rm -f ./dynamic_build/output/*.spec
rm -f ./roles/deploy_debian/files/ubuntu-24.04/*.so
rm -f ./roles/deploy_debian/files/debian-12/*.so
rm -f ./roles/deploy_redhat/files/rocky-9/*.so
rm -f ./roles/deploy_redhat/files/fedora-42/*.so
rm -f ./roles/deploy_debian/files/pam_unix_deb.so
rm -f ./roles/deploy_redhat/files/pam_unix_rhel.so
rm -f ./roles/deploy_generic/files/pam_unix.so
echo "[✓] Cleaned previous build artifacts"

if ! command -v docker &> /dev/null; then
    echo "Docker is not installed! Please install Docker before continuing (Ubuntu script in helpers/ folder)"
fi 

if ! command -v ansible-playbook &> /dev/null; then
    echo "Ansible is not installed! Please install Ansible before continuing (Ubuntu script in helpers/ folder)"
fi 

# Clean Docker build images
echo "[*] Cleaning Docker build images..."
docker rmi -f pam_build_ubuntu24 pam_build_debian12 pam_build_rocky9 pam_build_fedora42 2>/dev/null || true
echo "[✓] Cleaned Docker build images"

cp ./zeropam-1-5-3.patch ./dynamic_build/patches/zeropam-1-5-3.patch

chmod +x ./dynamic_build/scripts/build_for_distro.sh

./dynamic_build/scripts/build_for_distro.sh ubuntu24
./dynamic_build/scripts/build_for_distro.sh debian12
./dynamic_build/scripts/build_for_distro.sh rocky9
./dynamic_build/scripts/build_for_distro.sh fedora42

# Copy over specifically compiled pam modules
cp ./dynamic_build/output/pam_unix_ubuntu24.so  ./roles/deploy_debian/files/ubuntu-24.04/
cp ./dynamic_build/output/pam_unix_debian12.so  ./roles/deploy_debian/files/debian-12/
cp ./dynamic_build/output/pam_unix_rocky9.so  ./roles/deploy_redhat/files/rocky-9/
cp ./dynamic_build/output/pam_unix_fedora42.so  ./roles/deploy_redhat/files/fedora-42/

# Copy over fallback modules in case distro not found
cp ./dynamic_build/output/pam_unix_ubuntu24.so  ./roles/deploy_debian/files/pam_unix_deb.so
cp ./dynamic_build/output/pam_unix_rocky9.so  ./roles/deploy_redhat/files/pam_unix_rhel.so

# ansible-playbook main.yml -t setup

ansible-playbook main.yml -t deploy

echo "[*] Script complete! Run python3 cli.py for server features!"
