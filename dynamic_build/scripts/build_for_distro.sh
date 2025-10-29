#!/usr/bin/env bash
set -euo pipefail

DISTRO=$1
PATCH=$(realpath ./dynamic_build/patches/zeropam-1-5-3.patch)
OUTDIR=$(realpath ./dynamic_build/output)
mkdir -p "$OUTDIR"

case "$DISTRO" in
  ubuntu24) DOCKERFILE="./dynamic_build/Dockerfiles/Dockerfile.ubuntu24" ;;
  debian12) DOCKERFILE="./dynamic_build/Dockerfiles/Dockerfile.debian12" ;;
  rocky9)   DOCKERFILE="./dynamic_build/Dockerfiles/Dockerfile.rocky9" ;;
  fedora42) DOCKERFILE="./dynamic_build/Dockerfiles/Dockerfile.fedora42" ;;
  *) echo "Unsupported distro: $DISTRO" && exit 1 ;;
esac

IMAGE="pam_build_${DISTRO}"

echo "[*] Building container image for $DISTRO..."
docker build -t $IMAGE -f $DOCKERFILE .

echo "[*] Running build process for $DISTRO..."
docker run --rm -v "$OUTDIR":/out -v "$PATCH":/tmp/zeropam.patch $IMAGE bash -c "
  set -e
  mkdir -p /build && cd /build

  if [[ '$DISTRO' == ubuntu* || '$DISTRO' == debian* ]]; then
    apt-get source pam
    cd pam-*
    mkdir -p debian/patches/
    cp /tmp/zeropam.patch debian/patches/
    echo 'zeropam.patch' >> debian/patches/series
    debuild -b -uc -us
    find .. -name pam_unix.so -exec cp {} /out/pam_unix_${DISTRO}.so \;
  else
    dnf download --source pam
    rpm -ivh pam-*.src.rpm
    cd ~/rpmbuild/SPECS
    cp /tmp/zeropam.patch ../SOURCES/
    # Find the last Patch line and add our patch after it
    LAST_PATCH_LINE=\$(grep -n '^Patch[0-9]*:' pam.spec | tail -1 | cut -d: -f1)
    sed -i \"\${LAST_PATCH_LINE}a Patch9999: zeropam.patch\" pam.spec
    # Replace %autosetup with commands to apply all patches including ours
    sed -i 's/^%autosetup.*/%autosetup -N\\n%autopatch\\n%patch9999 -p1/' pam.spec
    rpmbuild -ba pam.spec
    # After rpmbuild -ba pam.spec
    cd ~/rpmbuild/RPMS/x86_64
    rpm2cpio pam-*.rpm | cpio -idmv
    cp ./usr/lib64/security/pam_unix.so /out/pam_unix_${DISTRO}.so
    # ls -R /root/rpmbuild
    # find /root/rpmbuild/ -name \"*pam_unix.so\" -exec cp '{}' /out/pam_unix_${DISTRO}.so \;
  fi
"

echo "[+] Build complete for $DISTRO — output saved to $OUTDIR/pam_unix_${DISTRO}.so"