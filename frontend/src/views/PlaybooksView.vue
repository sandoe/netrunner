<template>
  <div class="playbooks-container">
    <div class="header">
      <h2><span class="glitch-text" data-text="AUTOMATION">AUTOMATION</span> PLAYBOOKS</h2>
      <button class="cyber-button primary" @click="openEditor(null)">+ NEW PLAYBOOK</button>
    </div>

    <div class="playbooks-grid">
      <div v-for="pb in playbooks" :key="pb.id" class="playbook-card" :class="{ 'inactive': !pb.is_active }">
        <div class="card-header">
          <div class="title">
            <span class="status-indicator" :class="{ 'active': pb.is_active }"></span>
            <h3>{{ pb.name }}</h3>
          </div>
          <div class="actions">
            <button class="icon-button" @click="toggleActive(pb)" :title="pb.is_active ? 'Disable' : 'Enable'">
              <span class="material-icons">{{ pb.is_active ? 'pause' : 'play_arrow' }}</span>
            </button>
            <button class="icon-button" @click="openEditor(pb)" title="Edit">
              <span class="material-icons">edit</span>
            </button>
            <button class="icon-button danger" @click="deletePlaybook(pb.id)" title="Delete">
              <span class="material-icons">delete</span>
            </button>
          </div>
        </div>
        <p class="description">{{ pb.description || 'No description provided.' }}</p>
        
        <div class="logic-summary">
          <div class="logic-block if-block">
            <strong>IF</strong>
            <div class="badges">
              <span class="badge condition" v-for="(cond, i) in safeParse(pb.conditions)" :key="i">
                {{ cond.field }} {{ cond.operator }} {{ cond.value }}
              </span>
              <span v-if="!safeParse(pb.conditions).length" class="badge empty">Always</span>
            </div>
          </div>
          <div class="logic-block then-block">
            <strong>THEN</strong>
            <div class="badges">
              <span class="badge action" v-for="(act, i) in safeParse(pb.actions)" :key="i">
                {{ formatActionType(act.type) }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Editor Modal -->
    <div v-if="showEditor" class="modal-overlay" @click.self="closeEditor">
      <div class="cyber-modal playbook-editor">
        <h3>{{ editingPlaybook.id ? 'EDIT' : 'NEW' }} PLAYBOOK</h3>
        
        <div class="form-group">
          <label>Name</label>
          <input type="text" v-model="editingPlaybook.name" class="cyber-input" placeholder="e.g. Block Critical Malware" />
        </div>
        <div class="form-group">
          <label>Description</label>
          <input type="text" v-model="editingPlaybook.description" class="cyber-input" placeholder="Briefly describe what this does..." />
        </div>
        
        <div class="logic-builder">
          <h4>CONDITIONS (IF)</h4>
          <div class="builder-list">
            <div v-for="(cond, index) in editingConditions" :key="index" class="builder-row">
              <select v-model="cond.field" class="cyber-select">
                <option value="severity">Severity</option>
                <option value="type">Threat Type</option>
                <option value="source_ip">Source IP</option>
              </select>
              <select v-model="cond.operator" class="cyber-select operator">
                <option value="==">Equals (==)</option>
                <option value="!=">Not Equals (!=)</option>
              </select>
              <input type="text" v-model="cond.value" class="cyber-input value" placeholder="Value" />
              <button class="icon-button danger" @click="editingConditions.splice(index, 1)">
                <span class="material-icons">close</span>
              </button>
            </div>
            <button class="text-button" @click="editingConditions.push({field: 'severity', operator: '==', value: 'critical'})">+ Add Condition</button>
          </div>

          <h4 class="mt-4">ACTIONS (THEN)</h4>
          <div class="builder-list">
            <div v-for="(act, index) in editingActions" :key="index" class="builder-row">
              <select v-model="act.type" class="cyber-select action-select">
                <option value="block_ip">Block Source IP (IPTables)</option>
                <option value="isolate_node">Isolate Target Node (Quarantine)</option>
                <option value="auto_close">Auto-Close Alert (False Positive)</option>
              </select>
              <button class="icon-button danger" @click="editingActions.splice(index, 1)">
                <span class="material-icons">close</span>
              </button>
            </div>
            <button class="text-button" @click="editingActions.push({type: 'block_ip'})">+ Add Action</button>
          </div>
        </div>

        <div class="modal-actions">
          <button class="cyber-button" @click="closeEditor">CANCEL</button>
          <button class="cyber-button primary" @click="savePlaybook">SAVE PLAYBOOK</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { 
  listPlaybooksPlaybooksGet,
  updatePlaybookPlaybooksPlaybookIdPatch,
  deletePlaybookPlaybooksPlaybookIdDelete,
  createPlaybookPlaybooksPost
} from '@/api_client'
import type { PlaybookResponse } from '@/api_client'

const playbooks = ref<PlaybookResponse[]>([])
const showEditor = ref(false)

const editingPlaybook = ref<any>({})
const editingConditions = ref<any[]>([])
const editingActions = ref<any[]>([])

const fetchPlaybooks = async () => {
  try {
    const res = await listPlaybooksPlaybooksGet()
    playbooks.value = res.data || []
    playbooks.value = res as unknown as PlaybookResponse[]
  } catch (err) {
    console.error("Failed to load playbooks", err)
  }
}

onMounted(() => {
  fetchPlaybooks()
})

const safeParse = (str: string) => {
  try {
    return JSON.parse(str || '[]')
  } catch {
    return []
  }
}

const formatActionType = (type: string) => {
  const map: Record<string, string> = {
    'block_ip': 'Block IP',
    'isolate_node': 'Isolate Node',
    'auto_close': 'Auto-Close'
  }
  return map[type] || type
}

const toggleActive = async (pb: PlaybookResponse) => {
  try {
    await updatePlaybookPlaybooksPlaybookIdPatch({
      path: { playbook_id: pb.id },
      body: { is_active: !pb.is_active }
    })
    pb.is_active = !pb.is_active
  } catch (err) {
    console.error(err)
  }
}

const deletePlaybook = async (id: string) => {
  if (!confirm("Are you sure you want to delete this playbook?")) return
  try {
    await deletePlaybookPlaybooksPlaybookIdDelete({ path: { playbook_id: id } })
    await fetchPlaybooks()
  } catch (err) {
    console.error(err)
  }
}

const openEditor = (pb: PlaybookResponse | null) => {
  if (pb) {
    editingPlaybook.value = { ...pb }
    editingConditions.value = safeParse(pb.conditions)
    editingActions.value = safeParse(pb.actions)
  } else {
    editingPlaybook.value = { name: '', description: '', is_active: true }
    editingConditions.value = []
    editingActions.value = []
  }
  showEditor.value = true
}

const closeEditor = () => {
  showEditor.value = false
}

const savePlaybook = async () => {
  try {
    const body = {
      name: editingPlaybook.value.name,
      description: editingPlaybook.value.description,
      is_active: editingPlaybook.value.is_active ?? true,
      conditions: JSON.stringify(editingConditions.value),
      actions: JSON.stringify(editingActions.value)
    }

    if (editingPlaybook.value.id) {
      await updatePlaybookPlaybooksPlaybookIdPatch({
        path: { playbook_id: editingPlaybook.value.id },
        body
      })
    } else {
      await createPlaybookPlaybooksPost({ body })
    }
    
    closeEditor()
    await fetchPlaybooks()
  } catch (err) {
    console.error("Failed to save", err)
    alert("Failed to save playbook")
  }
}
</script>

<style scoped>
.playbooks-container {
  padding: 2rem;
  color: var(--text-color);
  max-width: 1200px;
  margin: 0 auto;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
  border-bottom: 1px solid var(--accent-blue);
  padding-bottom: 1rem;
}

.header h2 {
  font-family: 'Orbitron', sans-serif;
  color: var(--accent-blue);
  margin: 0;
  text-shadow: 0 0 10px rgba(0, 240, 255, 0.3);
}

.playbooks-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 1.5rem;
}

.playbook-card {
  background: rgba(10, 15, 30, 0.8);
  border: 1px solid var(--accent-blue);
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.5);
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.playbook-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0; height: 3px;
  background: var(--accent-blue);
  box-shadow: 0 0 10px var(--accent-blue);
}

.playbook-card.inactive {
  opacity: 0.6;
  border-color: #555;
}
.playbook-card.inactive::before {
  background: #555;
  box-shadow: none;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
}

.card-header .title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.card-header h3 {
  margin: 0;
  font-size: 1.2rem;
  color: #fff;
}

.status-indicator {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #ff3366;
  box-shadow: 0 0 8px #ff3366;
}
.status-indicator.active {
  background: #00ffcc;
  box-shadow: 0 0 8px #00ffcc;
}

.actions {
  display: flex;
  gap: 0.5rem;
}

.icon-button {
  background: transparent;
  border: none;
  color: var(--accent-blue);
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  transition: background 0.2s;
}
.icon-button:hover {
  background: rgba(0, 240, 255, 0.1);
}
.icon-button.danger {
  color: #ff3366;
}
.icon-button.danger:hover {
  background: rgba(255, 51, 102, 0.1);
}

.description {
  color: #aaa;
  font-size: 0.9rem;
  margin-bottom: 1.5rem;
  line-height: 1.4;
}

.logic-summary {
  background: rgba(0,0,0,0.4);
  padding: 1rem;
  border-radius: 4px;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.logic-block {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.logic-block strong {
  font-size: 0.8rem;
  color: #888;
  letter-spacing: 1px;
}

.badges {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.badge {
  padding: 0.2rem 0.6rem;
  border-radius: 12px;
  font-size: 0.8rem;
  font-weight: 600;
  background: rgba(255,255,255,0.1);
}
.badge.condition {
  background: rgba(0, 240, 255, 0.15);
  color: var(--accent-blue);
  border: 1px solid rgba(0, 240, 255, 0.3);
}
.badge.action {
  background: rgba(255, 51, 102, 0.15);
  color: #ff3366;
  border: 1px solid rgba(255, 51, 102, 0.3);
}

/* Modal Styles */
.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.8);
  backdrop-filter: blur(5px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.cyber-modal {
  background: var(--bg-dark);
  border: 1px solid var(--accent-blue);
  border-radius: 8px;
  padding: 2rem;
  width: 90%;
  max-width: 600px;
  box-shadow: 0 0 30px rgba(0, 240, 255, 0.2);
  max-height: 90vh;
  overflow-y: auto;
}

.cyber-modal h3 {
  font-family: 'Orbitron', sans-serif;
  color: var(--accent-blue);
  margin-top: 0;
  margin-bottom: 1.5rem;
  border-bottom: 1px solid rgba(0, 240, 255, 0.3);
  padding-bottom: 0.5rem;
}

.form-group {
  margin-bottom: 1.5rem;
}
.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  color: #ccc;
  font-size: 0.9rem;
}

.cyber-input, .cyber-select {
  width: 100%;
  background: rgba(0,0,0,0.5);
  border: 1px solid rgba(0, 240, 255, 0.3);
  color: #fff;
  padding: 0.8rem;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
}
.cyber-input:focus, .cyber-select:focus {
  outline: none;
  border-color: var(--accent-blue);
  box-shadow: 0 0 10px rgba(0, 240, 255, 0.2);
}

.logic-builder {
  background: rgba(0,0,0,0.3);
  border: 1px dashed rgba(255,255,255,0.2);
  padding: 1.5rem;
  border-radius: 4px;
  margin-bottom: 2rem;
}
.logic-builder h4 {
  margin-top: 0;
  color: #888;
  font-size: 0.9rem;
  letter-spacing: 1px;
}
.mt-4 {
  margin-top: 1.5rem !important;
}

.builder-list {
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
}
.builder-row {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}
.builder-row .cyber-select {
  flex: 1;
}
.builder-row .operator {
  max-width: 120px;
}
.builder-row .value {
  flex: 2;
}

.text-button {
  background: none;
  border: none;
  color: var(--accent-blue);
  cursor: pointer;
  text-align: left;
  padding: 0.5rem 0;
  font-size: 0.9rem;
}
.text-button:hover {
  text-decoration: underline;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
}

.cyber-button {
  padding: 0.8rem 1.5rem;
  background: transparent;
  border: 1px solid var(--accent-blue);
  color: var(--accent-blue);
  cursor: pointer;
  font-weight: bold;
  letter-spacing: 1px;
  transition: all 0.3s;
}
.cyber-button:hover {
  background: rgba(0, 240, 255, 0.1);
  box-shadow: 0 0 15px rgba(0, 240, 255, 0.3);
}
.cyber-button.primary {
  background: var(--accent-blue);
  color: #000;
}
.cyber-button.primary:hover {
  background: #00e0ee;
  box-shadow: 0 0 20px rgba(0, 240, 255, 0.5);
}
</style>
