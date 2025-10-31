#!/usr/bin/env bash
set -euo pipefail

DISTRO=$1
PATCH=$(realpath ./dynamic_build/patches/zeropam-1-5-3.patch)
OUTDIR=$(realpath ./dynamic_build/output)
mkdir -p "$OUTDIR"

case "$DISTRO" in
  ubuntu24) DOCKERFILE="./dynamic_build/Dockerfiles/Dockerfile.ubuntu24" ;;
  ubuntu22) DOCKERFILE="./dynamic_build/Dockerfiles/Dockerfile.ubuntu22" ;;
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
    
    # For Debian/Ubuntu, add patch to the patches-applied directory which persists through clean
    if [[ '$DISTRO' == ubuntu24 ]]; then
      mkdir -p debian/patches/
      cp /tmp/zeropam.patch debian/patches/zeropam.patch
      
      # Add to patches/series so it gets applied during build
      if [ -f debian/patches/series ]; then
        echo 'zeropam.patch' >> debian/patches/series
      else
        echo 'zeropam.patch' > debian/patches/series
      fi
      
      echo '[*] Added zeropam.patch to debian/patches/series'
    else
      mkdir -p debian/patches-applied/
      cp /tmp/zeropam.patch debian/patches-applied/zeropam.patch
      
      # Add to patches-applied/series so it gets applied during build
      if [ -f debian/patches-applied/series ]; then
        echo 'zeropam.patch' >> debian/patches-applied/series
      else
        echo 'zeropam.patch' > debian/patches-applied/series
      fi
      
      echo '[*] Added zeropam.patch to debian/patches-applied/series'
      
      echo '[*] Added zeropam.patch to debian/patches-applied/series'
    fi

    echo '[*] Verifying patch applied to source...'
    if grep -q 'USER AUTHENTICATED:' modules/pam_unix/pam_unix_auth.c 2>/dev/null; then
      echo '[✓] Patch already applied to source code'
    else
      echo '[*] Patch will be applied during build by dh_quilt_patch'
    fi
    
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

    LAST_PREP_PATCH_LINE=\$(grep -n '^%patch[0-9]*' pam.spec | tail -1 | cut -d: -f1)
    if [[ '$DISTRO' == rocky* ]]; then
      sed -i \"\${LAST_PREP_PATCH_LINE}a %patch9999 -p1 -b .zeropam\" pam.spec
    else
      sed -i \"\${LAST_PREP_PATCH_LINE}a %patch 9999 -p1 -b .zeropam\" pam.spec
    fi

    echo '[*] Building with rpmbuild (patch will be applied)...'
    rpmbuild -ba pam.spec

    echo '[*] Verifying patch applied to built source...'
    if grep -q 'USER AUTHENTICATED:' ~/rpmbuild/BUILD/pam-*/modules/pam_unix/pam_unix_auth.c 2>/dev/null; then
      echo '[✓] Patch applied to source code'
    else
      echo '[✗] WARNING: Could not verify patch in source (may still be in binary)'
    fi

    # After rpmbuild -ba pam.spec
    cd ~/rpmbuild/RPMS/x86_64
    rpm2cpio pam-*.rpm | cpio -idmv
    cp ./usr/lib64/security/pam_unix.so /out/pam_unix_${DISTRO}.so
  fi
"

echo "[+] Build complete for $DISTRO — output saved to $OUTDIR/pam_unix_${DISTRO}.so"