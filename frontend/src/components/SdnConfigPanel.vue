<template>
  <div class="sdn-config-panel">
    <div class="panel-header">
      <h2>🌐 SDN CONTROLLER</h2>
    </div>

    <!-- VLAN Configuration -->
    <div class="glass-panel" style="margin-bottom: 20px;">
      <h3 style="display: flex; align-items: center; gap: 10px; color: var(--cyan);">
        <svg xmlns="http://www.w3.org/2000/svg" style="width: 20px; height: 20px; stroke: currentColor;" fill="none" viewBox="0 0 24 24" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 002-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
        </svg>
        VLAN CONFIGURATION
      </h3>

      <div style="display: flex; gap: 10px; margin-top: 15px; margin-bottom: 15px; flex-wrap: wrap;">
        <input v-model="newVlan.tag" type="number" placeholder="VLAN Tag (e.g. 10)" class="hack-input" style="flex: 1; min-width: 150px;" />
        <input v-model="newVlan.name" type="text" placeholder="Name (e.g. Guest)" class="hack-input" style="flex: 2; min-width: 150px;" />
        <input v-model="newVlan.subnet" type="text" placeholder="Subnet (e.g. 192.168.10.0/24)" class="hack-input" style="flex: 2; min-width: 150px;" />
        <button @click="addVlan" class="btn-cyan" style="flex: 1; min-width: 150px;">
          [ ADD VLAN ]
        </button>
      </div>

      <table class="data-table">
        <thead>
          <tr>
            <th>TAG</th>
            <th>NAME</th>
            <th>SUBNET</th>
            <th style="text-align: right;">ACTIONS</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="vlan in vlans" :key="vlan.id">
            <td>{{ vlan.tag }}</td>
            <td>{{ vlan.name }}</td>
            <td style="font-family: monospace; color: var(--cyan);">{{ vlan.subnet }}</td>
            <td style="text-align: right;">
              <button @click="deleteVlan(vlan.id)" class="ctrl-btn delete-btn" title="Delete VLAN">✕</button>
            </td>
          </tr>
          <tr v-if="vlans.length === 0">
            <td colspan="4" style="text-align: center; color: var(--text-muted); font-style: italic;">No VLANs configured</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- NAT Rules -->
    <div class="glass-panel">
      <h3 style="display: flex; align-items: center; gap: 10px; color: var(--pink);">
        <svg xmlns="http://www.w3.org/2000/svg" style="width: 20px; height: 20px; stroke: currentColor;" fill="none" viewBox="0 0 24 24" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
        </svg>
        NAT RULES
      </h3>

      <div style="display: flex; gap: 10px; margin-top: 15px; margin-bottom: 15px; flex-wrap: wrap;">
        <select v-model="newNat.type" class="hack-input" style="flex: 1; min-width: 100px; appearance: auto;">
          <option value="snat">SNAT</option>
          <option value="dnat">DNAT</option>
          <option value="1:1">1:1 NAT</option>
          <option value="port-forward">Port Forward</option>
        </select>
        <input v-model="newNat.src" type="text" placeholder="Source IP/Net" class="hack-input" style="flex: 2; min-width: 120px;" />
        <input v-model="newNat.dst" type="text" placeholder="Dest IP/Net" class="hack-input" style="flex: 2; min-width: 120px;" />
        <input v-model="newNat.port" type="number" placeholder="Port (opt)" class="hack-input" style="flex: 1; min-width: 90px;" />
        <button @click="addNatRule" class="btn-action" style="flex: 1; min-width: 120px; border-color: var(--pink); color: var(--pink);">
          [ ADD RULE ]
        </button>
      </div>

      <table class="data-table">
        <thead>
          <tr>
            <th>TYPE</th>
            <th>SOURCE</th>
            <th>DESTINATION</th>
            <th>PORT</th>
            <th style="text-align: right;">ACTIONS</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="rule in natRules" :key="rule.id">
            <td>
              <span style="background: rgba(255, 45, 110, 0.2); border: 1px solid var(--pink); color: var(--pink); padding: 2px 6px; border-radius: 4px; font-size: 10px; text-transform: uppercase;">
                {{ rule.type }}
              </span>
            </td>
            <td style="font-family: monospace;">{{ rule.src }}</td>
            <td style="font-family: monospace;">{{ rule.dst }}</td>
            <td style="font-family: monospace;">{{ rule.port || 'ANY' }}</td>
            <td style="text-align: right;">
              <button @click="deleteNatRule(rule.id)" class="ctrl-btn delete-btn" title="Delete Rule">✕</button>
            </td>
          </tr>
          <tr v-if="natRules.length === 0">
            <td colspan="5" style="text-align: center; color: var(--text-muted); font-style: italic;">No NAT rules configured</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';

const vlans = ref([]);
const natRules = ref([]);

const newVlan = ref({ tag: null, name: '', subnet: '' });
const newNat = ref({ type: 'snat', src: '', dst: '', port: null });

const fetchVlans = async () => {
  try {
    const res = await fetch('/api/v1/sdn/vlans', {
      headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
    });
    if (res.ok) {
      vlans.value = await res.json();
    }
  } catch (err) {
    console.error('Failed to fetch VLANs', err);
  }
};

const addVlan = async () => {
  if (!newVlan.value.tag || !newVlan.value.name || !newVlan.value.subnet) return;
  try {
    const res = await fetch('/api/v1/sdn/vlans', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      },
      body: JSON.stringify({
        tag: parseInt(newVlan.value.tag),
        name: newVlan.value.name,
        subnet: newVlan.value.subnet
      })
    });
    if (res.ok) {
      newVlan.value = { tag: null, name: '', subnet: '' };
      fetchVlans();
    }
  } catch (err) {
    console.error('Failed to add VLAN', err);
  }
};

const deleteVlan = async (id) => {
  try {
    const res = await fetch(`/api/v1/sdn/vlans/${id}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
    });
    if (res.ok) {
      fetchVlans();
    }
  } catch (err) {
    console.error('Failed to delete VLAN', err);
  }
};

const fetchNatRules = async () => {
  try {
    const res = await fetch('/api/v1/sdn/nat', {
      headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
    });
    if (res.ok) {
      natRules.value = await res.json();
    }
  } catch (err) {
    console.error('Failed to fetch NAT rules', err);
  }
};

const addNatRule = async () => {
  if (!newNat.value.src || !newNat.value.dst) return;
  try {
    const res = await fetch('/api/v1/sdn/nat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      },
      body: JSON.stringify({
        type: newNat.value.type,
        src: newNat.value.src,
        dst: newNat.value.dst,
        port: newNat.value.port ? parseInt(newNat.value.port) : null
      })
    });
    if (res.ok) {
      newNat.value = { type: 'snat', src: '', dst: '', port: null };
      fetchNatRules();
    }
  } catch (err) {
    console.error('Failed to add NAT rule', err);
  }
};

const deleteNatRule = async (id) => {
  try {
    const res = await fetch(`/api/v1/sdn/nat/${id}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
    });
    if (res.ok) {
      fetchNatRules();
    }
  } catch (err) {
    console.error('Failed to delete NAT rule', err);
  }
};

onMounted(() => {
  fetchVlans();
  fetchNatRules();
});
</script>

<style scoped>
.sdn-config-panel {
  padding: 10px;
}
</style>
