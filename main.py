import requests, json, time
import meraki
import ast
import re
import netaddr
from netaddr import IPNetwork, IPAddress
import ipaddress

# Author: Mithchell Gulledge

# class that contains all Meraki necessary config
class MerakiConfig:
    api_key = ''
    org_name = ''
    org_id = None
    auth = meraki.DashboardAPI(api_key)
    header = {"X-Cisco-Meraki-API-Key": api_key, "Content-Type": "application/json"}

# writing function to obtain org ID via linking ORG name
result_org_id = MerakiConfig.auth.organizations.getOrganizations()
for x in result_org_id:
    if x['name'] == MerakiConfig.org_name:
        MerakiConfig.org_id = x['id']

# writing function to obtain BGP config, only variable needed is network ID for Hub
def get_hub_bgp_config(network_id):
    # the BGP URL listed below
    get_bgp_url = 'https://api.meraki.com/api/v1/networks/'+network_id+'/appliance/vpn/bgp'
    # since we are not using SDK we need to craft header
    header = {"X-Cisco-Meraki-API-Key": MerakiConfig.api_key, "Content-Type": "application/json"}
    bgp_config = requests.get(get_bgp_url, headers=header).content
    print(bgp_config)

# function to determine if string has digits
def hasNumbers(inputString):
    return bool(re.search(r'\d', inputString))

# this function performs an org wide Meraki call for all sites VPN statuses
# creating a list that we will append all sites names + prefixes to
site_address_list = []
# not using the SDK for this call as it is currently unavailable for now..
def org_wide_vpn_status():
    # defining the URL for the GET below
    org_vpn_url = 'https://api.meraki.com/api/v1/organizations/'\
        +MerakiConfig.org_id+'/appliance/vpn/statuses?'
    # performing API call to meraki dashboard
    vpn_statuses = requests.get(org_vpn_url, headers=MerakiConfig.header).content
    # vpn_status is a data type of bytes, going to convert to a string then adictionary
    decoded_vpn_statuses = vpn_statuses[1:-1].decode("UTF-8") # parsing outer brackets
    # converting string to dictionary
    meraki_vpn_peers = ast.literal_eval(decoded_vpn_statuses)
    # iterating through list of dictionaries and pulling site name with exported subnets
    for sites in meraki_vpn_peers:
        # validating that there is a digit in the exported subnets otherwise skip
        if hasNumbers(str(sites['exportedSubnets'])) == True:
            # creating variable that contains branch prefix 
            branch_prefix = {"siteName" : sites['networkName'] , "siteSubnet" : sites['exportedSubnets'][0]['subnet']}
            # appending branch prefixes to list of addresses
            site_address_list.append(branch_prefix)

# function that verifies if an IP address is inside a prefix
def ip_in_prefix(ip_address, prefix):
    if IPAddress(str(ip_address)) in IPNetwork(str(prefix)):
        return True


# writing function to update BGP config, statically assigning BGP values
def update_hub_bgp_config(network_id):
    # the BGP URL listed below
    get_bgp_url = 'https://api.meraki.com/api/v1/networks/'+network_id+'/appliance/vpn/bgp'

    bgp_data = '{"enabled":true,"asNumber":64515,"ibgpHoldTimer":240,"neighbors":[{"ip":"172.31.1.25",\
        "remoteAsNumber":3000,"receiveLimit":160,"allowTransit":true,"ebgpHoldTimer":180,"ebgpMultihop":2}]}'


    bgp_config = requests.put(get_bgp_url, headers=MerakiConfig.header, data=bgp_data).content
    print(bgp_config)

# writing function to obtain the BGP established log in the events api
def get_bgp_events_api(network_id):
    # event api url
    event_url = 'https://api.meraki.com/api/v1/networks/'+network_id+'/events/eventTypes'
    # request to get all BGP Events
    events = requests.get(event_url, headers=MerakiConfig.header).content
    # converting from data type of bytes to list
    events_string = events.decode("utf8")
    # converting from string to list of dictionaries
    events_list = json.loads(events_string)
    print(events_list[-1])
    # iterating through the list of events_list to match all BGP events
    for event in events_list:
        if event['category'] == 'BGP':
            print(event)

# writing function to obtain the BGP established log in the events api
def get_detailed_bgp_events_api(network_id, site_address_list):
    # full event api url
    full_event_url = 'https://api.meraki.com/api/v1/networks/'+network_id+'/events'
    # parameters for limiting event types to include BGP only
    bgp_data = '{"includedEventTypes":"BGP"}'
    # request to get all BGP Events
    full_events = requests.get(full_event_url, headers=MerakiConfig.header, data=bgp_data).content
    # converting from data type of bytes to list
    full_events_string = full_events.decode("utf8")
    # converting from string to list of dictionaries
    full_events_list = json.loads(full_events_string)
    # parsing out the event data to just get list of events
    list_of_bgp_events = full_events_list['events']
    # iterating through list and matching BGP events
    for bgp_event in list_of_bgp_events:
        if bgp_event['type'] == 'bgp_session_unestablished' or \
            bgp_event['type'] == 'bgp_sent_notification' or \
                bgp_event['type'] == 'bgp_received_notification' or \
                    bgp_event['type'] == 'bgp_sent_notification' or \
                        bgp_event['type'] == 'bgp_session_established': 
                            # iterating through site list
                            for ip_address in site_address_list:
                                formatted_ip = str(bgp_event['eventData']['peer_ip'])
                                is_in_prefix = ip_in_prefix(formatted_ip, ip_address['siteSubnet'])
                                # if is_in_prefix function returns true, we will match event with sitename
                                if is_in_prefix == True:
                                    print(str(bgp_event['type']) + " to " + str(ip_address['siteName']) + " occurred at " + str(bgp_event['occurredAt'][-9]))

print("current BGP config below")
get_hub_bgp_config('N_647955396388003951')
print("current events showing BGP")
get_bgp_events_api('N_647955396388003951')
print("org wide statuses below")
org_wide_vpn_status()
print("updated BGP config")
update_hub_bgp_config('N_647955396388003951')
print("list of site addresses (prefix/name)")
print(site_address_list)
print("current detailed events showing BGP")
get_detailed_bgp_events_api('N_647955396388003951', site_address_list)
