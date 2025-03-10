import ansible_runner

def ping_cmd(ip):
    print(f"Pinging {ip}")
    r = ansible_runner.run(
        private_data_dir='.',
        inventory="ansible/inventory.ini",
        host_pattern=ip,
        module='ping', 
    )
    print("{}: {}".format(r.status, r.rc))
    for each_host_event in r.events:
        print(each_host_event['event'])
    print("Final status:")
    print(r.stats)