<template>
  <div class="cyberdeck-codex">
    <!-- Book Navigation Header -->
    <div class="codex-header">
      <div class="header-title">
        <span class="icon">📖</span> CYBERDECK CODEX :: DATABANK v1.0
      </div>
      <div class="header-actions">
        <button class="btn-action" :disabled="currentPage <= 0" @click="prevPage">[ < PREV ]</button>
        <span class="page-indicator">PAGE {{ Math.floor(currentPage/2) + 1 }} / {{ Math.floor(pages.length/2) + 1 }}</span>
        <button class="btn-action" :disabled="currentPage >= pages.length - 2" @click="nextPage">[ NEXT > ]</button>
      </div>
    </div>

    <!-- The 3D Book Container -->
    <div class="book-container">
      <div class="book" :class="{'is-flipping': isFlipping}">
        <!-- LEFT PAGE -->
        <div class="page page-left">
          <div class="page-content" v-html="leftPageContent"></div>
          <div class="page-number" v-if="currentPage > 0">{{ currentPage }}</div>
        </div>

        <!-- BINDING -->
        <div class="book-spine"></div>

        <!-- RIGHT PAGE -->
        <div class="page page-right">
          <div class="page-content" v-html="rightPageContent"></div>
          <div class="page-number" v-if="currentPage + 1 < pages.length">{{ currentPage + 1 }}</div>
        </div>

        <!-- FAKE FLIPPING PAGE (For animation) -->
        <div class="page-flipper" :class="flipDirection" v-show="isFlipping">
          <div class="flipper-front" v-html="flipperFrontContent"></div>
          <div class="flipper-back" v-html="flipperBackContent"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

const isFlipping = ref(false)
const flipDirection = ref<'next' | 'prev'>('next')
const currentPage = ref(0) // Even numbers are left pages (0, 2, 4...)
const isLoading = ref(true)

interface CodexPage {
  title: string
  content: string
}

const pages = ref<string[]>([])

onMounted(async () => {
  try {
    const res = await fetch('/data/codex.json')
    if (res.ok) {
      const data: CodexPage[] = await res.json()
      pages.value = data.map(p => p.content)
    } else {
      console.error('Failed to load codex.json')
      pages.value = ['<h1>ERROR: CODEX OFFLINE</h1>', '<h1>ERROR: NO DATA</h1>']
    }
  } catch (err) {
    console.error(err)
    pages.value = ['<h1>ERROR: CODEX OFFLINE</h1>', '<h1>ERROR: CONNECTION LOST</h1>']
  } finally {
    isLoading.value = false
  }
})

const leftPageContent = computed(() => pages.value[currentPage.value] || '')
const rightPageContent = computed(() => pages.value[currentPage.value + 1] || '')

const flipperFrontContent = computed(() => {
  if (flipDirection.value === 'next') return pages.value[currentPage.value + 1] || ''
  return pages.value[currentPage.value] || ''
})

const flipperBackContent = computed(() => {
  if (flipDirection.value === 'next') return pages.value[currentPage.value + 2] || ''
  return pages.value[currentPage.value - 1] || ''
})

function nextPage() {
  if (currentPage.value >= pages.value.length - 2 || isFlipping.value) return

  flipDirection.value = 'next'

  isFlipping.value = true

  setTimeout(() => {
    currentPage.value += 2
    isFlipping.value = false
  }, 600) // matches css transition time
}

function prevPage() {
  if (currentPage.value <= 0 || isFlipping.value) return

  flipDirection.value = 'prev'

  isFlipping.value = true

  setTimeout(() => {
    currentPage.value -= 2
    isFlipping.value = false
  }, 600)
}
</script>

<style scoped>
.cyberdeck-codex {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg-darker);
  color: var(--text);
  font-family: var(--font-co);
}

.codex-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 20px;
  background: rgba(0, 229, 255, 0.05);
  border-bottom: 1px solid rgba(0, 229, 255, 0.2);
}

.header-title {
  font-family: var(--font-hd);
  color: var(--cyan);
  letter-spacing: 2px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 15px;
}

.page-indicator {
  font-size: 12px;
  color: var(--text-muted);
}

.btn-action {
  background: transparent;
  border: 1px solid var(--cyan);
  color: var(--cyan);
  padding: 4px 10px;
  cursor: pointer;
  font-family: var(--font-co);
  transition: all 0.2s;
}

.btn-action:hover:not(:disabled) {
  background: rgba(0, 229, 255, 0.2);
}

.btn-action:disabled {
  opacity: 0.3;
  cursor: not-allowed;
  border-color: var(--text-muted);
  color: var(--text-muted);
}

/* Book Container */
.book-container {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  perspective: 1500px;
  padding: 20px;
  overflow: hidden;
}

.book {
  display: flex;
  width: 800px;
  height: 500px;
  position: relative;
  transform-style: preserve-3d;
  box-shadow: 0 0 30px rgba(0, 229, 255, 0.1);
}

/* Spine */
.book-spine {
  width: 40px;
  height: 100%;
  background: linear-gradient(to right, #0a111a, #1a2a3a, #0a111a);
  position: absolute;
  left: calc(50% - 20px);
  z-index: 5;
  box-shadow: inset 0 0 10px rgba(0,0,0,0.8);
}

/* Pages */
.page {
  flex: 1;
  background: #080c14;
  border: 1px solid rgba(0, 229, 255, 0.3);
  padding: 40px;
  position: relative;
  overflow: hidden;
  box-shadow: inset 0 0 50px rgba(0, 0, 0, 0.8);
}

.page-left {
  border-right: none;
  border-top-left-radius: 4px;
  border-bottom-left-radius: 4px;
  background: linear-gradient(to right, #080c14 80%, #0d1624 100%);
}

.page-right {
  border-left: none;
  border-top-right-radius: 4px;
  border-bottom-right-radius: 4px;
  background: linear-gradient(to left, #080c14 80%, #0d1624 100%);
}

.page-number {
  position: absolute;
  bottom: 20px;
  font-family: var(--font-hd);
  color: rgba(0, 229, 255, 0.3);
}
.page-left .page-number { left: 20px; }
.page-right .page-number { right: 20px; }

/* Flipper Animation */
.page-flipper {
  position: absolute;
  top: 0;
  width: 50%;
  height: 100%;
  transform-style: preserve-3d;
  transform-origin: left center;
  transition: transform 0.6s cubic-bezier(0.645, 0.045, 0.355, 1);
  z-index: 10;
}

.page-flipper.next {
  left: 50%;
  transform-origin: left center;
  transform: rotateY(0deg);
}
.book.is-flipping .page-flipper.next {
  transform: rotateY(-180deg);
}

.page-flipper.prev {
  left: 50%;
  transform-origin: left center;
  transform: rotateY(-180deg);
}
.book.is-flipping .page-flipper.prev {
  transform: rotateY(0deg);
}

.flipper-front, .flipper-back {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  backface-visibility: hidden;
  background: #080c14;
  border: 1px solid rgba(0, 229, 255, 0.3);
  padding: 40px;
  box-shadow: inset 0 0 50px rgba(0, 0, 0, 0.8);
}

.page-flipper.next .flipper-front {
  background: linear-gradient(to left, #080c14 80%, #0d1624 100%);
}
.page-flipper.next .flipper-back {
  transform: rotateY(180deg);
  background: linear-gradient(to right, #080c14 80%, #0d1624 100%);
}

.page-flipper.prev .flipper-back {
  background: linear-gradient(to right, #080c14 80%, #0d1624 100%);
}
.page-flipper.prev .flipper-front {
  transform: rotateY(180deg);
  background: linear-gradient(to left, #080c14 80%, #0d1624 100%);
}

/* Page Content Styling (Applied via v-html) */
:deep(.page-content), :deep(.flipper-front), :deep(.flipper-back) {
  height: 100%;
  overflow-y: auto;
  padding-right: 10px;
}

:deep(h1), :deep(h2), :deep(h3), :deep(h4) {
  font-family: var(--font-hd);
  color: var(--cyan);
  margin-top: 0;
}
:deep(h3) { border-bottom: 1px dashed rgba(0,229,255,0.3); padding-bottom: 5px; margin-bottom: 20px;}
:deep(h4) { color: var(--pink); margin-bottom: 5px; margin-top: 20px;}
:deep(p) { line-height: 1.6; margin-bottom: 15px; font-size: 13px; color: var(--textwh); }
:deep(b) { color: var(--cyan); }
:deep(i) { color: var(--text-muted); }
:deep(ul) { padding-left: 20px; line-height: 1.6; font-size: 13px; }
:deep(li) { margin-bottom: 8px; }

:deep(.cover) {
  text-align: center;
  display: flex;
  flex-direction: column;
  justify-content: center;
  height: 100%;
}
:deep(.cover h1) { font-size: 36px; margin-bottom: 5px; }
:deep(.cover h2) { color: var(--text-muted); font-size: 16px; margin-bottom: 40px;}
:deep(.cover .ascii-art) {
  font-family: monospace;
  white-space: pre;
  color: var(--pink);
  margin-bottom: 40px;
  opacity: 0.8;
}

/* Scrollbar */
:deep(::-webkit-scrollbar) { width: 4px; }
:deep(::-webkit-scrollbar-track) { background: rgba(0,0,0,0.2); }
:deep(::-webkit-scrollbar-thumb) { background: var(--cyan); border-radius: 2px; }
</style>
