#!/usr/bin/env bash
set -euo pipefail

# Script to verify that the zeropam patch was applied to compiled PAM modules
# Usage: ./verify_patch.sh [path/to/pam_unix.so] or run without args to check all in output/

OUTDIR="${1:-./dynamic_build/output}"

# Unique strings added by our patch
MARKERS=(
    "USER AUTHENTICATED:"
    "USER CHANGED PASSWORD:"
    "SUDO SESSION OPENED:"
)

verify_file() {
    local file="$1"
    local found_count=0
    local total=${#MARKERS[@]}
    
    echo ""
    echo "=========================================="
    echo "Verifying: $(basename "$file")"
    echo "=========================================="
    
    if [[ ! -f "$file" ]]; then
        echo "[✗] File not found: $file"
        return 1
    fi
    
    # Check file type
    if ! file "$file" | grep -q "ELF.*shared object"; then
        echo "[✗] Not a valid shared object file"
        return 1
    fi
    
    # Check each marker string
    for marker in "${MARKERS[@]}"; do
        if strings "$file" | grep -q "$marker"; then
            echo "[✓] Found: '$marker'"
            ((found_count++))
        else
            echo "[✗] Missing: '$marker'"
        fi
    done
    
    echo ""
    echo "Result: $found_count/$total markers found"
    
    if [[ $found_count -eq $total ]]; then
        echo "[✓] VERIFICATION PASSED"
        return 0
    else
        echo "[✗] VERIFICATION FAILED"
        return 1
    fi
}

# Main execution
if [[ -f "$OUTDIR" ]]; then
    # Single file provided
    verify_file "$OUTDIR"
    exit $?
elif [[ -d "$OUTDIR" ]]; then
    # Directory provided - check all .so files
    echo "Scanning directory: $OUTDIR"
    
    failed_count=0
    passed_count=0
    
    for so_file in "$OUTDIR"/pam_unix_*.so; do
        if [[ -f "$so_file" ]]; then
            if verify_file "$so_file"; then
                ((passed_count++))
            else
                ((failed_count++))
            fi
        fi
    done
    
    echo ""
    echo "=========================================="
    echo "SUMMARY"
    echo "=========================================="
    echo "Passed: $passed_count"
    echo "Failed: $failed_count"
    echo ""
    
    if [[ $failed_count -eq 0 && $passed_count -gt 0 ]]; then
        echo "[✓] All verifications PASSED"
        exit 0
    else
        echo "[✗] Some verifications FAILED"
        exit 1
    fi
else
    echo "Error: Path not found: $OUTDIR"
    echo "Usage: $0 [path/to/pam_unix.so|directory]"
    exit 1
fi
