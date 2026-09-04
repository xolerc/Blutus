# ============================================================
# backend/services/cloud_scanner.py
# ============================================================
import asyncio
import subprocess
import socket
import ipaddress
import nmap
import boto3
import google.cloud.compute_v1 as gcp
import azure.mgmt.compute as azure_compute
from typing import List, Dict, Optional
import aiohttp
import json
import re

class CloudScanner:
    """Real cloud scanner with all providers."""
    
    def __init__(self):
        self.nm = nmap.PortScanner()
        self.targets = []
        
    async def scan_aws(self, region: str) -> List[Dict]:
        """Scan AWS EC2 instances."""
        try:
            ec2 = boto3.client('ec2', region_name=region)
            instances = ec2.describe_instances()
            results = []
            for reservation in instances['Reservations']:
                for instance in reservation['Instances']:
                    if instance['State']['Name'] == 'running':
                        for network in instance.get('NetworkInterfaces', []):
                            for ip in network.get('PrivateIpAddresses', []):
                                results.append({
                                    'ip': ip.get('PrivateIpAddress'),
                                    'public_ip': instance.get('PublicIpAddress'),
                                    'instance_id': instance['InstanceId'],
                                    'provider': 'aws',
                                    'region': region,
                                    'os': self._detect_os(instance),
                                    'ports': []
                                })
            return results
        except Exception as e:
            print(f"AWS scan error: {e}")
            return []

    async def scan_gcp(self, project_id: str) -> List[Dict]:
        """Scan GCP Compute instances."""
        try:
            client = gcp.InstancesClient()
            instances = client.list(project=project_id)
            results = []
            for instance in instances:
                for network in instance.network_interfaces:
                    results.append({
                        'ip': network.network_i_p,
                        'public_ip': network.access_configs[0].nat_i_p if network.access_configs else None,
                        'instance_id': instance.id,
                        'provider': 'gcp',
                        'region': instance.zone.split('/')[-1],
                        'os': instance.machine_type,
                        'ports': []
                    })
            return results
        except Exception as e:
            print(f"GCP scan error: {e}")
            return []

    async def scan_azure(self, subscription_id: str) -> List[Dict]:
        """Scan Azure VMs."""
        try:
            compute_client = azure_compute.ComputeManagementClient()
            vms = compute_client.virtual_machines.list_all()
            results = []
            for vm in vms:
                results.append({
                    'ip': vm.properties.network_profile.network_interfaces[0].id,
                    'instance_id': vm.id,
                    'provider': 'azure',
                    'region': vm.location,
                    'os': vm.properties.os_profile.computer_name,
                    'ports': []
                })
            return results
        except Exception as e:
            print(f"Azure scan error: {e}")
            return []

    async def scan_public_ranges(self) -> List[Dict]:
        """Scan public cloud IP ranges."""
        results = []
        # Common cloud ranges
        ranges = [
            ('3.0.0.0', '3.255.255.255', 'aws'),
            ('52.0.0.0', '52.255.255.255', 'aws'),
            ('34.0.0.0', '34.255.255.255', 'gcp'),
            ('13.0.0.0', '13.255.255.255', 'azure'),
            ('159.0.0.0', '159.255.255.255', 'digitalocean'),
        ]
        
        for start, end, provider in ranges:
            start_ip = ipaddress.ip_address(start)
            end_ip = ipaddress.ip_address(end)
            # Sample random IPs from range
            for i in range(100):
                try:
                    ip = str(ipaddress.ip_address(int(start_ip) + random.randint(0, int(end_ip) - int(start_ip))))
                    if await self._ping_host(ip):
                        hostname = await self._get_hostname(ip)
                        results.append({
                            'ip': ip,
                            'hostname': hostname,
                            'provider': provider,
                            'region': 'discovered',
                            'ports': []
                        })
                except:
                    continue
        return results

    async def scan_local_network(self) -> List[Dict]:
        """Scan local network via ARP."""
        results = []
        try:
            result = subprocess.run(['arp', '-a'], capture_output=True, text=True)
            lines = result.stdout.split('\n')
            for line in lines:
                match = re.search(r'(\d+\.\d+\.\d+\.\d+)', line)
                if match:
                    ip = match.group(1)
                    if await self._ping_host(ip):
                        hostname = await self._get_hostname(ip)
                        results.append({
                            'ip': ip,
                            'hostname': hostname,
                            'provider': 'local',
                            'region': 'local',
                            'ports': []
                        })
        except Exception as e:
            print(f"ARP scan error: {e}")
        return results

    async def scan_ports(self, target: Dict) -> Dict:
        """Port scan using nmap."""
        try:
            ip = target['ip']
            self.nm.scan(ip, '1-65535', '-T4 -sS -sV')
            
            ports = []
            for proto in self.nm[ip].all_protocols():
                for port in self.nm[ip][proto].keys():
                    service = self.nm[ip][proto][port]
                    ports.append({
                        'port': port,
                        'protocol': proto,
                        'service': service.get('name', 'unknown'),
                        'version': service.get('version', ''),
                        'product': service.get('product', ''),
                        'banner': service.get('banner', '')
                    })
            
            target['ports'] = ports
            target['os'] = self.nm[ip].get('osclass', [{}])[0].get('osfamily', 'unknown')
            return target
        except Exception as e:
            print(f"Port scan error: {e}")
            return target

    async def _ping_host(self, ip: str) -> bool:
        try:
            result = subprocess.run(['ping', '-c', '1', '-W', '1', ip], capture_output=True)
            return result.returncode == 0
        except:
            return False

    async def _get_hostname(self, ip: str) -> str:
        try:
            return socket.gethostbyaddr(ip)[0]
        except:
            return 'unknown'

    def _detect_os(self, instance: Dict) -> str:
        # AWS OS detection
        tags = instance.get('Tags', [])
        for tag in tags:
            if tag['Key'] == 'OS':
                return tag['Value']
        # Check platform
        if 'Platform' in instance:
            return instance['Platform']
        return 'unknown'
