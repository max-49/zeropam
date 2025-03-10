import ansible_runner

def ping_cmd(ip):
    r = ansible_runner.run(
        private_data_dir='.',
        inventory=f"{ip}",
        host_pattern=ip,
        module='ping', 
        extravars={
            'ansible_user': 'ccdc',
            'ansible_password': 'ccdc', 
        }
    )