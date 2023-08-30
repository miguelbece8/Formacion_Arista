#l!/usr/bin/python3
#from cvplibrary import CVPGlobalVariables, GlobalVariableNames
import json
import yaml
import ssl
#from cvplibrary import RestClient


#hostname = CVPGlobalVariables.getValue(GlobalVariableNames.CVP_SYSTEM_LABELS)
hostname = input ("Obtner configuración de: ")

#tags = CVPGlobalVariables.getValue(GlobalVariableNames.CVP_SYSTEM_LABELS)


#for item in tags:
#  key, value = item.split(':')
#  if key == 'hostname':
#    hostname = value
    
#ssl._create_default_https_context = ssl._create_unverified_context
#configlet = 'config_yaml'
#cvp_url = 'https://192.168.0.5/cvpservice/'
#client = RestClient(cvp_url+'configlet/getConfigletByName.do?name='+configlet,'GET')

#if client.connect():
#  raw = json.loads(client.getResponse())
#
#underlay = yaml.safe_load(raw['config'])
#

file = open('network_topology.yml', 'r')
underlay_yaml = file.read()
underlay = yaml.safe_load(underlay_yaml)

prefix_list = """
ip prefix-list loopback
    seq 10 permit 192.168.101.0/24 eq 32
    seq 11 permit 192.168.102.0/24 eq 32
    seq 12 permit 192.168.201.0/24 eq 32
    seq 13 permit 192.168.202.0/24 eq 32
    seq 14 permit 192.168.253.0/24 eq 32
    
route-map LOOPBACK permit 10
  no match ip address prefix-list LOOPBACK
  match ip address prefix-list loopback
"""

peer_filter = """
peer-filter LEAF-AS-RANGE
  10 match as-range 65000-65535 result accept
"""

def gen_interfaces():
  for iface in underlay[hostname]['interfaces']:
    print("interface %s") % iface
    ip = underlay[hostname]['interfaces'][iface]['ipv4']
    mask = underlay[hostname]['interfaces'][iface]['mask']
    mtu = underlay['global']['MTU']
    print("  ip address %s/%s") % (ip, mask)
    if "Ethernet" in iface:
        print("  no switchport")
        print("  mtu %s") % mtu
      

def gen_spine_underlay():
  print(prefix_list)
  print(peer_filter)
  ASN = underlay[hostname]['BGP']['ASN']
  lo0 = underlay[hostname]['interfaces']['loopback0']['ipv4']
  print("router bgp", ASN)
  print("  router-id",  lo0)
  print("  no bgp default ipv4-unicast")
  print("  maximum-paths 3")
  print("  distance bgp 20 200 200")
  print("  ")
  print("  neighbor LEAF_Underlay peer group")
  if "DC1" in hostname:
    p2p = underlay['global']['DC1']['p2p']
    print("  bgp listen range", p2p ,"peer-group LEAF_Underlay peer-filter LEAF-AS-RANGE")
  if "DC2" in hostname:
    p2p = underlay['global']['DC2']['p2p']
    print("  bgp listen range", p2p ,"peer-group LEAF_Underlay peer-filter LEAF-AS-RANGE")
  print("  neighbor LEAF_Underlay send-community")
  print("  neighbor LEAF_Underlay maximum-routes 12000")
  print("  ")
  print("  neighbor EVPN peer group")
  
  if "DC1" in hostname:
    lo0 = underlay['global']['DC1']['lo0']
  if "DC2" in hostname:
    lo0 = underlay['global']['DC2']['lo0']
    
  print("  bgp listen range", lo0 ,"peer-group EVPN peer-filter LEAF-AS-RANGE")
  print("  neighbor EVPN update-source Loopback0")
  print("  neighbor EVPN ebgp-multihop 3")
  print("  neighbor EVPN send-community extended")
  print("  neighbor EVPN maximum-routes 0")
  
  print("  ")
  
  print("  redistribute connected route-map LOOPBACK")
  
  print("  ")
  print("  address-family evpn")
  print("    neighbor EVPN activate")
  print("  address-family ipv4")
  print("    neighbor LEAF_Underlay activate")
  print("    redistribute connected route-map LOOPBACK")
  
def gen_leaf_underlay():
  print(prefix_list)
  print(peer_filter)
  ASN = underlay[hostname]['BGP']['ASN']
  lo0 = underlay[hostname]['interfaces']['loopback0']['ipv4']
  print("router bgp ",  ASN)
  print("  router-id ", lo0)
  print("  no bgp default ipv4-unicast")
  print("  maximum-paths 3")
  print("  distance bgp 20 200 200")
  
  print("  neighbor Underlay peer group")
  spine_ASN = underlay[hostname]['BGP']['spine-ASN']
  print("  neighbor Underlay remote-as", spine_ASN)
  print("  neighbor Underlay send-community")
  print("  neighbor Underlay maximum-routes 12000")
  for spine_peer in underlay[hostname]['BGP']['spine-peers']:
    print("  neighbor", spine_peer, "peer group Underlay")
  
  print("  ")
  
  print("  neighbor LEAF_Peer peer group")
  print("  neighbor LEAF_Peer remote-as",  ASN)
  print("  neighbor LEAF_Peer next-hop-self")
  print("  neighbor LEAF_Peer maximum-routes 12000")
  if (underlay[hostname]['MLAG'] == 'Odd'):
    print("  neighbor 192.168.255.2 peer group LEAF_Peer")
  if (underlay[hostname]['MLAG'] == 'Even'):
    print("  neighbor 192.168.255.1 peer group LEAF_Peer") 
  
  print("  ")
  
  print("  neighbor EVPN peer group")
  spine_ASN = underlay[hostname]['BGP']['spine-ASN']
  print("  neighbor EVPN remote-as",  spine_ASN)
  print("  neighbor EVPN update-source Loopback0")
  print("  neighbor EVPN ebgp-multihop 3")
  print("  neighbor EVPN send-community")
  print("  neighbor EVPN maximum-routes 0")  
  
  if "DC1" in hostname:
    for spine_peer in underlay['global']['DC1']['spine_peers']:
      print("  neighbor", spine_peer, "peer group EVPN")
  if "DC2" in hostname:
    for spine_peer in underlay['global']['DC2']['spine_peers']:
      print("  neighbor", spine_peer, "peer group EVPN")  
      
  print("  ")
  
  if "borderleaf" in hostname:
    print("  neighbor DCI peer group")
    print("  neighbor DCI send-community")
    print("  neighbor DCI maximum-routes 12000")
    DCI_ASN = underlay[hostname]['BGP']['DCI-ASN']
    print("  neighbor DCI remote-as", DCI_ASN)
    if "borderleaf1-DC1" in hostname:
      for DCI_peer in underlay[hostname]['BGP']['DCI-peers']:
        print("  neighbor", DCI_peer ,"peer group DCI")
    if "borderleaf1-DC2" in hostname:
      for DCI_peer in underlay[hostname]['BGP']['DCI-peers']:
        print("  neighbor", DCI_peer ,"peer group DCI")
    if "borderleaf2-DC1" in hostname:
      for DCI_peer in underlay[hostname]['BGP']['DCI-peers']:
        print("  neighbor", DCI_peer ,"peer group DCI")
    if "borderleaf2-DC2" in hostname:
      for DCI_peer in underlay[hostname]['BGP']['DCI-peers']:
        print("  neighbor", DCI_peer ,"peer group DCI")
  
  print("  ")
  
  print("  redistribute connected route-map LOOPBACK")
  
  print("  ")
  print("  address-family evpn")
  print("    neighbor EVPN activate")
  print("  address-family ipv4")
  print("    neighbor Underlay activate")
  print("    neighbor LEAF_Peer activate")
  print("    neighbor DCI activate")
  print("    redistribute connected route-map LOOPBACK")
  

#gen_interfaces()
if "spine" in hostname:
  gen_spine_underlay()
if "leaf" in hostname:
  gen_leaf_underlay()


