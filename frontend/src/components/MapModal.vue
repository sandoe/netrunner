<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="cyber-modal-card map-modal" role="dialog" aria-modal="true" aria-labelledby="map-modal-title">
      <div class="cyber-modal-header">
        <div class="modal-title" id="map-modal-title">📌 TRACKER MAP - {{ title }}</div>
        <button class="btn-close-modal" @click="$emit('close')">×</button>
      </div>
      <div class="cyber-modal-body" style="padding: 0;">
        <div id="map-container" style="height: 400px; width: 100%;"></div>
        
        <div class="map-overlay-data" v-if="latestLocation">
          <div><span class="lbl">LAT:</span> {{ latestLocation.lat.toFixed(5) }}</div>
          <div><span class="lbl">LON:</span> {{ latestLocation.lon.toFixed(5) }}</div>
          <div><span class="lbl">CITY:</span> {{ latestLocation.city || 'UNKNOWN' }}</div>
          <div><span class="lbl">ISP/NETWORK:</span> {{ latestLocation.isp || 'UNKNOWN' }}</div>
        </div>
      </div>
      <div class="cyber-modal-footer">
        <div class="warning-text">
          <span v-if="!hasGpsHardware" class="text-orange">⚠️ WARNING: Using IP-based network triangulation. Precision is low (Data Center level). Hardware GPS required for street-level accuracy.</span>
        </div>
        <button class="btn-action" @click="$emit('close')">CLOSE</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, onUnmounted } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

// Fix leaflet icon issues
import iconRetinaUrl from 'leaflet/dist/images/marker-icon-2x.png'
import iconUrl from 'leaflet/dist/images/marker-icon.png'
import shadowUrl from 'leaflet/dist/images/marker-shadow.png'

L.Icon.Default.mergeOptions({
  iconRetinaUrl,
  iconUrl,
  shadowUrl
})

onMounted(() => document.addEventListener('keydown', handleEscape))
function handleEscape(e: KeyboardEvent) {
  if (e.key === 'Escape') emit('close')
}

const props = defineProps<{
  title: string
  dataRaw: string
}>()

const emit = defineEmits(['close'])

const mapInstance = ref<L.Map | null>(null)
const latestLocation = ref<{ lat: number, lon: number, city?: string, isp?: string } | null>(null)
const hasGpsHardware = ref(false)

onMounted(() => {
  // Parse the JSONL data
  const lines = props.dataRaw.split('\n').filter(l => l.trim())
  const points = []
  
  for (const line of lines) {
    try {
      const obj = JSON.parse(line)
      if (obj.location && obj.location.lat && obj.location.lon) {
        points.push(obj.location)
      }
    } catch (e) {
      // ignore invalid lines
    }
  }

  if (points.length > 0) {
    latestLocation.value = points[points.length - 1]
    
    // Check if it's spoofed or if it has GPS tags (we assume IP if isp is present)
    hasGpsHardware.value = !latestLocation.value.isp
  }

  // Initialize map
  const defaultLat = latestLocation.value?.lat || 55.6761
  const defaultLon = latestLocation.value?.lon || 12.5683

  mapInstance.value = L.map('map-container', {
    zoomControl: false,
    attributionControl: false
  }).setView([defaultLat, defaultLon], 13)

  // Use a dark hacker-style basemap (CartoDB Dark Matter)
  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    subdomains: 'abcd',
    maxZoom: 19
  }).addTo(mapInstance.value)

  // Custom red marker
  const redIcon = new L.Icon({
    iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png',
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    shadowSize: [41, 41]
  });

  if (latestLocation.value) {
    L.marker([latestLocation.value.lat, latestLocation.value.lon], { icon: redIcon })
      .addTo(mapInstance.value)
      .bindPopup(`<b style="color:#000;">TARGET LOCATED</b><br>${latestLocation.value.city}`)
      .openPopup()
  }
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleEscape)
  if (mapInstance.value) {
    mapInstance.value.remove()
  }
})
</script>

<style scoped>
.map-modal {
  width: 700px;
  max-width: 90vw;
}

.map-overlay-data {
  position: absolute;
  top: 60px;
  right: 20px;
  background: rgba(10, 15, 20, 0.85);
  border: 1px solid var(--cyan);
  padding: 10px;
  z-index: 1000;
  pointer-events: none;
  font-family: var(--font-co);
  font-size: 11px;
  box-shadow: 0 0 10px rgba(0, 229, 255, 0.2);
}

.lbl {
  color: var(--cyan);
  font-weight: bold;
  margin-right: 5px;
}

@media (max-width: 768px) {
  .map-overlay-data {
    position: relative;
    top: auto;
    right: auto;
    margin: 10px;
  }
}

.warning-text {
  font-family: var(--font-co);
  font-size: 10px;
  flex-grow: 1;
}

.text-orange {
  color: #ff9900;
}
.btn-action:focus-visible, .btn-close-modal:focus-visible { outline: 2px solid var(--cyan); outline-offset: 2px; }
button:focus-visible, .btn-action:focus-visible, .btn-close:focus-visible { outline: 2px solid var(--cyan); outline-offset: 2px; }
</style>
