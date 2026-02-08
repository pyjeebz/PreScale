import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '@/views/Dashboard.vue'
import Agents from '@/views/Agents.vue'
import Predictions from '@/views/Predictions.vue'
import Anomalies from '@/views/Anomalies.vue'
import AgentInstall from '@/views/AgentInstall.vue'
import DeploymentsOverview from '@/views/DeploymentsOverview.vue'

const router = createRouter({
    history: createWebHistory(),
    routes: [
        {
            path: '/',
            name: 'dashboard',
            component: Dashboard
        },
        {
            path: '/agents',
            name: 'agents',
            component: Agents
        },
        {
            path: '/install',
            name: 'install',
            component: AgentInstall
        },
        {
            path: '/deployments',
            name: 'deployments',
            component: DeploymentsOverview
        },
        {
            path: '/predictions',
            name: 'predictions',
            component: Predictions
        },
        {
            path: '/anomalies',
            name: 'anomalies',
            component: Anomalies
        }
    ]
})

export default router

