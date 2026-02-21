import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useThemeStore = defineStore('theme', () => {
  const isDark = ref(true)

  function init() {
    const stored = localStorage.getItem('helios-theme')
    if (stored) {
      isDark.value = stored === 'dark'
    } else {
      isDark.value = true // Default to dark (Bento Grid aesthetic)
    }
    applyTheme()
  }

  function toggle() {
    isDark.value = !isDark.value
    localStorage.setItem('helios-theme', isDark.value ? 'dark' : 'light')
    applyTheme()
  }

  function setTheme(dark: boolean) {
    isDark.value = dark
    localStorage.setItem('helios-theme', dark ? 'dark' : 'light')
    applyTheme()
  }

  function applyTheme() {
    const root = document.documentElement
    if (isDark.value) {
      root.classList.add('dark')
      root.classList.remove('light')
    } else {
      root.classList.add('light')
      root.classList.remove('dark')
    }
  }

  return {
    isDark,
    init,
    toggle,
    setTheme
  }
})
