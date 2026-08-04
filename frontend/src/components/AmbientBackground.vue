<template>
  <div class="ambient-background">
    <vue-particles
      id="tsparticles"
      :options="particleOptions"
      @particles-loaded="particlesLoaded"
    />
    <div class="cyber-overlay" :class="themeClass"></div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  alertLevel?: 'normal' | 'elevated' | 'critical'
}>()

const themeClass = computed(() => {
  if (props.alertLevel === 'critical') return 'theme-critical'
  if (props.alertLevel === 'elevated') return 'theme-elevated'
  return 'theme-normal'
})

const particleOptions = computed(() => {
  const isCritical = props.alertLevel === 'critical'
  const isElevated = props.alertLevel === 'elevated'

  const particleColor = isCritical ? '#ff2d6e' : (isElevated ? '#f39c12' : '#00e5ff')
  const linkColor = isCritical ? '#ff2d6e' : (isElevated ? '#f39c12' : '#00e5ff')
  const speed = isCritical ? 6 : (isElevated ? 2 : 0.5)

  return {
    background: {
      color: {
        value: "transparent",
      },
    },
    fpsLimit: 60,
    interactivity: {
      events: {
        onHover: {
          enable: true,
          mode: "grab",
        },
      },
      modes: {
        grab: {
          distance: 140,
          links: {
            opacity: 0.8,
          },
        },
      },
    },
    particles: {
      color: {
        value: particleColor,
      },
      links: {
        color: linkColor,
        distance: 150,
        enable: true,
        opacity: 0.2,
        width: 1,
      },
      move: {
        direction: "none",
        enable: true,
        outModes: {
          default: "bounce",
        },
        random: false,
        speed: speed,
        straight: false,
      },
      number: {
        density: {
          enable: true,
          area: 800,
        },
        value: 60,
      },
      opacity: {
        value: 0.3,
      },
      shape: {
        type: "circle",
      },
      size: {
        value: { min: 1, max: 3 },
      },
    },
    detectRetina: true,
  }
})

const particlesLoaded = async (container: any) => {
  console.log("Particles loaded", container)
}
</script>

<style scoped>
.ambient-background {
  position: absolute;
  inset: 0;
  z-index: 0;
  overflow: hidden;
  pointer-events: none;
}

#tsparticles {
  position: absolute;
  inset: 0;
}

.cyber-overlay {
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at center, transparent 0%, rgba(8, 13, 24, 0.9) 100%);
  pointer-events: none;
  transition: background-color 1s ease;
  mix-blend-mode: overlay;
}

.theme-normal {
  background-color: rgba(0, 229, 255, 0.02);
}

.theme-elevated {
  background-color: rgba(243, 156, 18, 0.05);
}

.theme-critical {
  background-color: rgba(255, 45, 110, 0.1);
}
</style>
