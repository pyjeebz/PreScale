<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { RouterView, RouterLink, useRoute, useRouter } from 'vue-router'
import {
  Bars3Icon,
  XMarkIcon,
  HomeIcon,
  ServerStackIcon,
  ChartBarIcon,
  ExclamationTriangleIcon,
  SunIcon,
  MoonIcon,
  PlusIcon,
  CommandLineIcon,
  Square3Stack3DIcon,
  TrashIcon
} from '@heroicons/vue/24/outline'
import { useThemeStore } from '@/stores/theme'
import { useDeploymentsStore, type Deployment } from '@/stores/deployments'

const route = useRoute()
const router = useRouter()
const themeStore = useThemeStore()
const deploymentsStore = useDeploymentsStore()

const sidebarOpen = ref(false)
const deploymentDropdownOpen = ref(false)

const navigation = [
  { name: 'Dashboard', href: '/', icon: HomeIcon },
  { name: 'Agents', href: '/agents', icon: ServerStackIcon },
  { name: 'Predictions', href: '/predictions', icon: ChartBarIcon },
  { name: 'Anomalies', href: '/anomalies', icon: ExclamationTriangleIcon },
  { name: 'Deployments', href: '/deployments', icon: Square3Stack3DIcon }
]

function isActive(href: string) {
  if (href === '/') return route.path === '/'
  return route.path.startsWith(href)
}

function getEnvironmentBadge(env: string) {
  switch (env) {
    case 'production': return { text: 'prod', class: 'bg-green-500' }
    case 'staging': return { text: 'stg', class: 'bg-yellow-500' }
    case 'development': return { text: 'dev', class: 'bg-blue-500' }
    default: return { text: env, class: 'bg-slate-500' }
  }
}

function selectDeployment(id: string) {
  deploymentsStore.setCurrentDeployment(id)
  deploymentDropdownOpen.value = false
}

async function confirmDelete(deployment: Deployment) {
  if (confirm(`Are you sure you want to delete ${deployment.name}? This cannot be undone.`)) {
    try {
      await deploymentsStore.deleteDeployment(deployment.id)
      if (deploymentsStore.deployments.length === 0) {
        router.push('/install')
      }
    } catch (e) {
      alert('Failed to delete deployment')
    }
  }
}

function goToInstall() {
  deploymentDropdownOpen.value = false
  router.push('/install')
}

onMounted(() => {
  deploymentsStore.fetchDeployments()
})
</script>

<template>
  <div class="min-h-screen" style="background: var(--bg-primary); transition: background 0.3s ease;">
    <!-- Mobile sidebar overlay -->
    <div
      v-if="sidebarOpen"
      class="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
      @click="sidebarOpen = false"
    />

    <!-- Sidebar -->
    <aside
      :class="[
        'fixed inset-y-0 left-0 z-50 w-64 transform transition-transform lg:translate-x-0',
        sidebarOpen ? 'translate-x-0' : '-translate-x-full'
      ]"
      style="background: var(--bg-primary); border-right: 1px solid var(--border-primary);"
    >
      <!-- Logo -->
      <div class="h-16 flex items-center gap-3 px-6" style="border-bottom: 1px solid var(--border-primary);">
        <div class="w-8 h-8 rounded-lg flex items-center justify-center" style="background: var(--accent-gradient);">
          <span class="text-white font-bold text-sm">P</span>
        </div>
        <span class="text-lg font-semibold" style="color: var(--text-primary);">Prescale</span>
        <span class="ml-auto text-xs font-mono px-1.5 py-0.5 rounded" style="color: var(--text-tertiary); background: var(--bg-card); border: 1px solid var(--border-primary);">v0.2.0</span>
      </div>

      <!-- Navigation -->
      <nav class="p-4 space-y-1">
        <RouterLink
          v-for="item in navigation"
          :key="item.name"
          :to="item.href"
          :class="[
            'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 cursor-pointer',
          ]"
          :style="isActive(item.href) 
            ? 'background: rgba(99, 102, 241, 0.1); color: var(--accent-400);' 
            : 'color: var(--text-tertiary);'"
          @click="sidebarOpen = false"
          @mouseenter="($event.target as HTMLElement).style.color = isActive(item.href) ? 'var(--accent-400)' : 'var(--text-secondary)'"
          @mouseleave="($event.target as HTMLElement).style.color = isActive(item.href) ? 'var(--accent-400)' : 'var(--text-tertiary)'"
        >
          <component :is="item.icon" class="w-5 h-5" />
          {{ item.name }}
        </RouterLink>

        <!-- Install Agent link -->
        <RouterLink
          to="/install"
          class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 cursor-pointer"
          :style="route.path === '/install' 
            ? 'background: rgba(99, 102, 241, 0.1); color: var(--accent-400);' 
            : 'color: var(--text-tertiary);'"
          @click="sidebarOpen = false"
        >
          <CommandLineIcon class="w-5 h-5" />
          Install Agent
        </RouterLink>
      </nav>
    </aside>

    <!-- Main content -->
    <div class="lg:pl-64">
      <!-- Top bar -->
      <header 
        class="h-16 flex items-center justify-between px-4 lg:px-6"
        style="background: var(--bg-primary); border-bottom: 1px solid var(--border-primary);"
      >
        <button
          @click="sidebarOpen = true"
          class="lg:hidden p-2 rounded-lg transition-colors cursor-pointer"
          style="color: var(--text-tertiary);"
        >
          <Bars3Icon class="w-6 h-6" />
        </button>

        <div class="flex-1" />

        <!-- Deployment Selector -->
        <div class="relative mr-4" v-if="deploymentsStore.deployments.length > 0">
          <button
            @click="deploymentDropdownOpen = !deploymentDropdownOpen"
            class="flex items-center gap-2 px-3 py-1.5 rounded-lg transition-all duration-200 cursor-pointer"
            style="border: 1px solid var(--border-primary); color: var(--text-secondary);"
          >
            <span
              v-if="deploymentsStore.currentDeployment"
              :class="['w-2 h-2 rounded-full', getEnvironmentBadge(deploymentsStore.currentDeployment.environment).class]"
            ></span>
            <span class="text-sm font-medium">
              {{ deploymentsStore.currentDeployment?.name || 'Select Deployment' }}
            </span>
            <svg class="w-4 h-4" style="color: var(--text-tertiary);" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          <!-- Dropdown -->
          <div
            v-if="deploymentDropdownOpen"
            class="absolute right-0 mt-1 w-64 rounded-lg shadow-2xl py-1 z-50"
            style="background: var(--bg-elevated); border: 1px solid var(--border-primary);"
          >
            <div
              v-for="dep in deploymentsStore.deployments"
              :key="dep.id"
              class="flex items-center justify-between px-2 group transition-colors"
              :style="deploymentsStore.currentDeploymentId === dep.id 
                ? 'background: rgba(99, 102, 241, 0.1);' 
                : ''"
            >
              <button
                @click="selectDeployment(dep.id)"
                class="flex-1 flex items-center gap-2 py-2 px-1 text-sm text-left truncate cursor-pointer"
                style="color: var(--text-secondary);"
              >
                <span :class="['w-2 h-2 rounded-full flex-shrink-0', getEnvironmentBadge(dep.environment).class]"></span>
                <span class="truncate">{{ dep.name }}</span>
              </button>
              
              <button
                @click.stop="confirmDelete(dep)"
                class="p-1.5 rounded opacity-0 group-hover:opacity-100 transition-opacity hover:text-red-500 cursor-pointer"
                style="color: var(--text-tertiary);"
                title="Delete Deployment"
              >
                <TrashIcon class="w-4 h-4" />
              </button>
            </div>
            
            <div style="border-top: 1px solid var(--border-primary); margin: 0.25rem 0;"></div>
            
            <button
              @click="goToInstall"
              class="w-full flex items-center gap-2 px-3 py-2 text-sm text-left transition-colors cursor-pointer"
              style="color: var(--accent-400);"
            >
              <PlusIcon class="w-4 h-4" />
              Add Deployment
            </button>
          </div>
        </div>

        <!-- Theme toggle -->
        <button
          @click="themeStore.toggle()"
          class="p-2 rounded-lg transition-all duration-200 cursor-pointer"
          style="color: var(--text-tertiary);"
        >
          <SunIcon v-if="themeStore.isDark" class="w-5 h-5" />
          <MoonIcon v-else class="w-5 h-5" />
        </button>
      </header>

      <!-- Click outside to close dropdown -->
      <div v-if="deploymentDropdownOpen" class="fixed inset-0 z-40" @click="deploymentDropdownOpen = false"></div>

      <!-- Page content -->
      <main class="p-4 lg:p-6">
        <RouterView />
      </main>
    </div>
  </div>
</template>
