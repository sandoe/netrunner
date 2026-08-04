<template>
  <div class="terminal-content">
    <div v-for="(log, idx) in logs" :key="idx" class="log-entry">{{ log }}</div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  logs: string[]
}>()
</script>

<style scoped>
.terminal-content {
  padding: 1rem;
  overflow-y: auto;
  flex: 1;
  color: #a7f3d0;
  font-size: 0.9rem;
  line-height: 1.5;
}

.log-entry {
  margin-bottom: 0.3rem;
}
</style>
