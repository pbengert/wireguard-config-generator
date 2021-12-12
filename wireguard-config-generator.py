import qrcode
import subprocess
import sys
import os
import getopt
from dotenv import load_dotenv
load_dotenv()

# This program will generate configs for wireguard.
# you will need to install qrcode and pillow in python
# and you need to install wireguard, so that you can call wg from your terminal

################### Modify your settings here ##################

# Set the listen port

listen_port = f"{os.getenv('PORT')}"

# Set the endpoint
endpoint = f"{os.getenv('ENDPOINT_URL')}:{listen_port}"

# Number of needed clients
clients = int(os.getenv('NUMBER_OF_CLIENTS'))
# TODO add client Names
# Add ipv6 protocol to all Configs
# ipv6 = strToBool(os.getenv('IPV6'))

# Set preshared_key to True to create preshared keys or False if not needed
preshared_key = eval(os.getenv('PSK'))

# Set your DNS Server like "1.1.1.1" or empty string "" if not needed
# maybe you want to use a dns server on your server e.g. 192.168.1.1
dns = f"{os.getenv('DNS')}"

# Set your vpn tunnel network (example is for 10.99.99.0/24)
defaultTunnel = os.getenv('TUNNEL_NET').split('.')
ipnet_tunnel_1 = int(defaultTunnel[0])
ipnet_tunnel_2 = int(defaultTunnel[1])
ipnet_tunnel_3 = int(defaultTunnel[2])
ipnet_tunnel_4 = int(defaultTunnel[3].split('/')[0])
ipnet_tunnel_cidr = int(defaultTunnel[3].split('/')[1])

# Set allowed IPs (this should be the network of the server you want to access)
# If you want to route all traffic over the VPN then set tunnel_0_0_0_0 = True, the network in allowed ips will then be ignored
allowed_ips = f"{os.getenv('ALLOWEDIPS')}"
tunnel_0_0_0_0 = False

# If you need iptables rules then set iptables= "eth0" (replace eth0 with the name of your network card) or iptables = "" if no rules needed
iptables = f"{os.getenv('IPTABLES')}"

# Server name
serverName = f"{os.getenv('SERVER_NAME')}"

# Path to where interface config file will be stored
interfacePath = os.getenv('INTERFACE_CONFIG_LOCATION')

# Path where peers config and other files will be stored
clientPath = os.getenv('PEER_CONFIG_LOCATION')


################### Do not edit below this line ##################

wg_priv_keys = []
wg_pub_keys = []
wg_psk = []


def main(args):
    optionString = 'dhn:t:i:ac:f:'
    longOptions = ['default',
                    'help',
                    'port=',
                    'endpoint=',
                    'dns=',
                    'tunnel=',
                    'ipinterface=',
                    'allowedips=',
                    'clients=',
                    'psk=',
                    'ipv6=',
                    'file=',
                    'interfacepath=',
                    'clientpath=']
    try:
        options, remainder = getopt.getopt(args, optionString, longOptions)
    except getopt.GetoptError as e:
        print(e)
        print("For help refer to help manual, by running with option -h or --help, for more information")
        return
    # print 'OPTIONS   :', options

    optSet = set()
    for opt, arg in options:
        optSet.add(opt)
    
    if '-h' in optSet or '--help' in optSet:
        # TODO Create help message function
        display_help(optionString, longOptions)
        return
    elif '-d' in optSet or '--default' in optSet:
        print("Running with default configuration from .env")
        generate()
        return        

    if len(remainder) > 0:
        print(f"Error the following arguments, {remainder.join(',')} ,are not allowed. Please refer to help manual, by running with option -h or --help, for more information")

    for opt, arg in options:
        if opt in ('-f', '--file'):
            print(f"Processing {arg}")
            # TODO process JSON or YML files
            # processFile(arg)
            break
        elif opt in ('-n', '--dns'):
            dns = arg
        elif opt in ('-t', '--tunnel'):
            defaultTunnel = arg
        elif opt in ('-i', '--ipinterface'):
            iptables = arg
        elif opt in ('-a'):
            tunnel_0_0_0_0 = True
        elif opt in ('--allowedips'):
            allowed_ips = args
        elif opt in ('-c', '--clients'):
            clients = arg
            # TODO pass in client names and derive number of clients
        elif opt in ('--psk'):
            preshared_key = arg
        elif opt in ('--ipv6'):
            ipv6 = arg
            #TODO add ipv6 support
        elif opt in ('--interfacepath'):
            interfacepath = arg
        elif opt in ('--clientpath'):
            clientpath = arg

    # print 'OUTPUT    :', output_filename
    # print 'REMAINING :', remainder

def generate():
    #Validate inputs
    # TODO create validation for inputs/globals
    # Gen-Keys
    for x in range(clients+1):
        (privkey, pubkey, psk) = generate_wireguard_keys()
        #psk = generate_wireguard_psk()
        wg_priv_keys.append(privkey)
        wg_pub_keys.append(pubkey)
        wg_psk.append(psk)

    ################# Server-Config ##################
    server_config = f"[{serverName}]\n" \
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
    make_qr_code_png(server_config, f"{interfacePath}{serverName}.png")
    with open(f"{interfacePath}{serverName}.conf", "wt+") as f:
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
        make_qr_code_png(client_config, f"{clientPath}client_{i}.png")
        with open(f"{clientPath}client_{i}.conf", "wt+") as f:
            f.write(client_config)

    #print("*"*10 + " Debugging " + "*"*10 )
    #print("*"*10 + " Priv-Keys " + "*"*10 )
    # print(wg_priv_keys)
    #print("*"*10 + " Pub-Keys " + "*"*10 )
    # print(wg_pub_keys)


def generate_wireguard_keys():
    # privkey = subprocess.check_output(
    #     "wg genkey", shell=True).decode("utf-8").strip()
    # pubkey = subprocess.check_output(
    #     f"echo '{privkey}' | wg pubkey", shell=True).decode("utf-8").strip()
    # psk = subprocess.check_output(
    #     "wg genkey", shell=True).decode("utf-8").strip()

    privkey = f"TestPrivateKey" 
    pubkey = f"TestPublicKey" 
    psk = f"TestPresharedKey" 

    return (privkey, pubkey, psk)


def make_qr_code_png(text, filename):
    img = qrcode.make(text)
    img.save(f"{filename}")
    
def display_help(optionString,longOptions):
    print("Wireguard Config Generator\n\n")
    print("\tAllowed Options/Flags")
    print("\n\tAll options should be added with a single dash for short for or double dash with long form.")
    print("\tex: -d or --default")
    print("\tOptions should be followed by a colon, ':', for single dash flags or an equals sign, '=' for double dash flags.")
    print("\tex. -n:'8.8.8.8' or --dns='8.8.8.8'")
    print("\n\tHere is an example of multiple arguments being passed.")
    print("\tex. wireguard-config-generator.py -a -n:'8.8.8.8' --clients=3")

    for opt in optionString:
        if opt == ':':
            continue
        printOptionDefinition(f"-{opt}", getOptionDefinition(opt))
        
    for opt in longOptions:
        if '=' in opt:
            opt = opt[:-1]
        printOptionDefinition(f"--{opt}", getOptionDefinition(opt))

def printOptionDefinition(opt, definition):
    print("\n\n")
    print(f"\t\t {opt} \t\t\t {definition}")

def getOptionDefinition(opt):
    if opt in ('h', 'help'):
        return "Overrides all other flags and arguments and prints the help manual."
    elif opt in ('d', 'default'):
        return "Overrides an other options that are set and all variables are set to values in the .env file."
    elif opt in ('f', 'file'):
        return "Feature still in development."
        # return "Parameter: String. Takes a string path to the JSON file that can list the settings of multiple Interfaces and peers. All other setting and variables will be ignored. Example: python3 -f:'/user/directory/configs.json'"
    elif opt in ('n', 'dns'):
        return "Parameter: String. Sets the dns ip value for all peers. Leave blank if DNS is not needed on the peers."
    elif opt in ('t', 'tunnel'):
        return "Parameter: String. This sets the ip subnet for the tunnel on the interface."
    elif opt in ('i', 'ipinterface'):
        return "Parameter: String. This sets the name of the  Internet-facing interface. This may be ens2p0 or similar on more recent Ubuntu versions (check, e.g., 'ip a' for details about your local interfaces)."
    elif opt in ('a'):
        return "This option will forward all traffic from the peers to your interface."
    elif opt in ('allowedips'):
        return "Parameter: String. This will set the subnets that the peers will be allowed to connect to on the interface. The value should be comma seperated IPs."
    elif opt in ('c', 'clients'):
        return "Parameter: Integer. This will set the number of peers to be generated for the interface."
    elif opt in ('psk'):
        return "Parameter: Boolean. This will determine if there should be a preshared key generated for each peer."
    elif opt in ('ipv6'):
        return "Feature still in development."
    elif opt in ('interfacepath'):
        return "Paramter: String. This would be the path where the interface config of the server will be saved to."
    elif opt in ('clientpath'):
        return "Paramter: String. This would be the path where the all of the peer information including the QR codes will be saved to."
    elif opt in ('port'):
        return "Parameter: String. This should be the listening port set for the wireguard service. If the server is behind a device, e.g., a router that is doing NAT, be sure to forward the specified port on which WireGuard will be running from the router to the WireGuard server."
    elif opt in ('endpoint'):
        return "Parameter: String. This value should be set to your public ip or domain of the server you'd like to connect to."

if __name__ == "__main__":
    main(sys.argv[1:])
