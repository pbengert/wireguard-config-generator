import qrcode
import subprocess

# This program will generate configs for wireguard.
# you will need to install qrcode and pillow in python
# and you need to install wireguard, so that you can call wg from your terminal

################### Modify your settings here ##################

# Set the listen port

listen_port = "51820"

# Set the endpoint
endpoint = f"example.myip.com:{listen_port}"

# Number of needed clients
clients = 3

# Set preshared_key to True to create preshared keys or False if not needed
preshared_key = True

# Set your DNS Server like "1.1.1.1" or empty string "" if not needed
# maybe you want to use a dns server on your server e.g. 192.168.1.1
dns = "1.1.1.1"

# Set your vpn tunnel network (example is for 10.99.99.0/24)
ipnet_tunnel_1 = 10
ipnet_tunnel_2 = 99
ipnet_tunnel_3 = 99
ipnet_tunnel_4 = 0
ipnet_tunnel_cidr = 24

# Set allowed IPs (this should be the network of the server you want to access)
# If you want to route all traffic over the VPN then set tunnel_0_0_0_0 = True, the network in allowed ips will then be ignored
allowed_ips = "192.168.1.0/24"
tunnel_0_0_0_0 = False

# If you need iptables rules then set iptables= "eth0" (replace eth0 with the name of your network card) or iptables = "" if no rules needed
iptables = ""

################### Do not edit below this line ##################

wg_priv_keys = []
wg_pub_keys = []
wg_psk = []


def main():
    # Gen-Keys
    for _ in range(clients+1):
        (privkey, pubkey, psk) = generate_wireguard_keys()
        #psk = generate_wireguard_psk()
        wg_priv_keys.append(privkey)
        wg_pub_keys.append(pubkey)
        wg_psk.append(psk)

    ################# Server-Config ##################
    server_config = "[Interface]\n" \
        f"Address = {ipnet_tunnel_1}.{ipnet_tunnel_2}.{ipnet_tunnel_3}.{ipnet_tunnel_4+1}/{ipnet_tunnel_cidr}\n" \
        f"ListenPort = {listen_port}\n" \
        f"PrivateKey = {wg_priv_keys[0]}\n"
    if iptables:
        server_config += f"PostUp = iptables -A FORWARD -i %i -j ACCEPT; iptables -t nat -A POSTROUTING -o {iptables} -j MASQUERADE\n" \
            f"PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -t nat -D POSTROUTING -o {iptables} -j MASQUERADE\n"

    for i in range(1, clients+1):
        server_config += f"[Peer {i}]\n" \
            f"PublicKey = {wg_pub_keys[i]}\n" \
            f"PresharedKey = {wg_psk[i]}\n" \
            f"AllowedIPs = {ipnet_tunnel_1}.{ipnet_tunnel_2}.{ipnet_tunnel_3}.{ipnet_tunnel_4+1+i}/32\n"

    print("*"*10 + " Server-Conf " + "*"*10)
    print(server_config)
    make_qr_code_png(server_config, f"server.png")
    with open(f"server.conf", "wt") as f:
        f.write(server_config)

    ################# Client-Configs ##################
    client_configs = []
    for i in range(1, clients+1):
        client_config = f"[Interface]\n" \
            f"Address = {ipnet_tunnel_1}.{ipnet_tunnel_2}.{ipnet_tunnel_3}.{ipnet_tunnel_4+1+i}/24\n" \
            f"ListenPort = {listen_port}\n" \
            f"PrivateKey = {wg_priv_keys[i]}\n"

        if dns:
            client_config += f"DNS = {dns}\n"

        client_config += f"[Peer]\n" \
            f"PublicKey = {wg_pub_keys[0]}\n" \
            f"PresharedKey = {wg_psk[i]}\n"

        if tunnel_0_0_0_0 == False:
            client_config += f"AllowedIPs = {allowed_ips}, {ipnet_tunnel_1}.{ipnet_tunnel_2}.{ipnet_tunnel_3}.{ipnet_tunnel_4+1}/32\n"
        else:
            client_config += f"DNS = 0.0.0.0/0\n"

        client_config += f"Endpoint = {endpoint}\n"
        client_configs.append(client_config)

        print("*"*10 + f" Client-Conf {i} " + "*"*10)
        print(client_config)
        make_qr_code_png(client_config, f"client_{i}.png")
        with open(f"client_{i}.conf", "wt") as f:
            f.write(client_config)

    #print("*"*10 + " Debugging " + "*"*10 )
    #print("*"*10 + " Priv-Keys " + "*"*10 )
    # print(wg_priv_keys)
    #print("*"*10 + " Pub-Keys " + "*"*10 )
    # print(wg_pub_keys)


def generate_wireguard_keys():
    privkey = subprocess.check_output(
        "wg genkey", shell=True).decode("utf-8").strip()
    pubkey = subprocess.check_output(
        f"echo '{privkey}' | wg pubkey", shell=True).decode("utf-8").strip()
    psk = subprocess.check_output(
        "wg genkey", shell=True).decode("utf-8").strip()
    return (privkey, pubkey, psk)


def make_qr_code_png(text, filename):
    img = qrcode.make(text)
    img.save(f"{filename}")


if __name__ == "__main__":
    main()
