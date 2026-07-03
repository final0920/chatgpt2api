<template>
  <div class="inspect-page">
    <PagePanel class="space-y-4">
      <PanelHeader
        title="账号巡检"
        subtitle="删除 sub2api 错误账号；对命中 ChatGPT2API 号池的账号重新授权 → join 空间 → 推送 sub2api"
        align="start"
      >
        <template #actions>
          <StateBadge :tone="running ? 'success' : 'muted'" shape="rounded" size="sm">
            {{ running ? '巡检中' : '空闲' }}
          </StateBadge>
        </template>
      </PanelHeader>

      <SurfaceBox density="compact">
        <div class="inspect-toolbar">
          <div class="inspect-controls">
            <Checkbox :model-value="running" :disabled="toggling" @update:model-value="toggleInspect">
              {{ running ? '巡检运行中（取消勾选可停止）' : '开启巡检' }}
            </Checkbox>
            <label class="inspect-threads">
              线程
              <input
                class="inspect-threads-input"
                type="number"
                min="1"
                max="10"
                :value="threads"
                :disabled="running || toggling"
                @input="onThreadsInput"
              />
            </label>
            <label class="inspect-threads">
              代理
              <select
                class="inspect-proxy-select"
                :value="proxyMode"
                :disabled="running || toggling"
                @change="onProxyModeChange"
              >
                <option value="global">使用默认代理</option>
                <option value="direct">直连</option>
                <option value="group">代理组</option>
                <option value="custom">自定义代理</option>
              </select>
            </label>
            <label v-if="proxyMode === 'group'" class="inspect-threads">
              <select
                class="inspect-proxy-select"
                :value="selectedProxyGroupId"
                :disabled="running || toggling"
                @change="onProxyGroupChange"
              >
                <option value="">选择代理组</option>
                <option v-for="g in proxyGroups" :key="g.id" :value="g.id">{{ g.name }}</option>
              </select>
            </label>
            <label v-else-if="proxyMode === 'custom'" class="inspect-threads">
              <input
                class="inspect-proxy-input"
                type="text"
                placeholder="http://user:pass@host:port"
                :value="customProxyInput"
                :disabled="running || toggling"
                @input="onCustomProxyInput"
              />
            </label>
          </div>
          <div class="inspect-stats">
            <span>第 {{ stats.round }} 轮</span>
            <span>共 {{ stats.total }}</span>
            <span>删除 {{ stats.deleted }}</span>
            <span>命中 {{ stats.matched }}</span>
            <span>更新 {{ stats.synced }}</span>
            <span>失败 {{ stats.failed }}</span>
            <span>跳过 {{ stats.skipped }}</span>
          </div>
        </div>
        <div class="inspect-summary">
          <span>已完成 {{ stats.rounds_done }} 轮</span>
          <span>累计删除 {{ stats.total_deleted }}</span>
          <span>累计更新 {{ stats.total_synced }}</span>
          <span>累计失败 {{ stats.total_failed }}</span>
        </div>
      </SurfaceBox>

      <RuntimeLogPanel
        title="巡检日志"
        :lines="logLines"
        empty-title="暂无日志"
        empty-description="点击上方开启巡检后，这里会实时显示进度。"
        :min-height="360"
        :max-height="620"
      />
    </PagePanel>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { Checkbox } from 'nanocat-ui'
import { getAuthToken } from '@/api/client'
import { inspectApi, type InspectState } from '@/api/inspect'
import { proxyApi, parseProxyReference, serializeProxyReference, type ProxyGroup, type ProxyReferenceMode } from '@/api/proxy'
import { PagePanel, PanelHeader, RuntimeLogPanel, StateBadge, SurfaceBox, type RuntimeLogPanelLine } from '@/components/ai'
import { useToast } from '@/composables/useToast'

const toast = useToast()
const inspectState = ref<InspectState | null>(null)
const toggling = ref(false)
const threads = ref(3)
const proxyMode = ref<ProxyReferenceMode>('global')
const selectedProxyGroupId = ref('')
const customProxyInput = ref('')
const proxyGroups = ref<ProxyGroup[]>([])
const eventSource = ref<EventSource | null>(null)
const pollTimer = ref<number | null>(null)

const proxyRef = computed(() => {
  if (proxyMode.value === 'group') return serializeProxyReference('group', selectedProxyGroupId.value)
  if (proxyMode.value === 'custom') return serializeProxyReference('custom', customProxyInput.value)
  return serializeProxyReference(proxyMode.value)
})

const running = computed(() => Boolean(inspectState.value?.enabled || inspectState.value?.stats?.running))
const stats = computed(() => ({
  round: inspectState.value?.stats?.round ?? 0,
  total: inspectState.value?.stats?.total ?? 0,
  deleted: inspectState.value?.stats?.deleted ?? 0,
  matched: inspectState.value?.stats?.matched ?? 0,
  synced: inspectState.value?.stats?.synced ?? 0,
  failed: inspectState.value?.stats?.failed ?? 0,
  skipped: inspectState.value?.stats?.skipped ?? 0,
  rounds_done: inspectState.value?.stats?.rounds_done ?? 0,
  total_deleted: inspectState.value?.stats?.total_deleted ?? 0,
  total_synced: inspectState.value?.stats?.total_synced ?? 0,
  total_failed: inspectState.value?.stats?.total_failed ?? 0,
}))

function onThreadsInput(event: Event) {
  const raw = Number((event.target as HTMLInputElement).value)
  if (Number.isNaN(raw)) return
  threads.value = Math.max(1, Math.min(10, Math.trunc(raw)))
}

function onProxyModeChange(event: Event) {
  proxyMode.value = (event.target as HTMLSelectElement).value as ProxyReferenceMode
}

function onProxyGroupChange(event: Event) {
  selectedProxyGroupId.value = (event.target as HTMLSelectElement).value
}

function onCustomProxyInput(event: Event) {
  customProxyInput.value = (event.target as HTMLInputElement).value
}

function initProxyFromState() {
  const raw = inspectState.value?.proxy
  if (raw === undefined || raw === null) return
  const reference = parseProxyReference(raw)
  proxyMode.value = reference.mode === 'profile' ? 'custom' : reference.mode
  if (reference.mode === 'group') selectedProxyGroupId.value = reference.value
  else if (reference.mode === 'custom' || reference.mode === 'profile') customProxyInput.value = reference.value
}

async function loadProxyGroups() {
  try {
    const res = await proxyApi.listGroups()
    proxyGroups.value = res.groups || []
  } catch {
    /* 代理组拉取失败不阻塞巡检 */
  }
}

function normalizeLogLevel(level?: string) {
  if (level === 'red' || level === 'error') return 'error'
  if (level === 'green' || level === 'success') return 'success'
  if (level === 'yellow' || level === 'warning') return 'warning'
  return 'info'
}

function formatClock(value?: string) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleTimeString()
}

const logLines = computed<RuntimeLogPanelLine[]>(() => {
  const logs = inspectState.value?.logs || []
  return logs.slice().reverse().map((line, index) => ({
    key: `${line.time}-${index}`,
    time: formatClock(line.time),
    text: line.text,
    level: normalizeLogLevel(line.level),
  }))
})

function applyState(state: InspectState | null | undefined) {
  if (state) inspectState.value = state
}

async function loadState(silent = false) {
  try {
    const res = await inspectApi.getState()
    applyState(res.inspect)
  } catch {
    if (!silent) toast.error('加载巡检状态失败')
  }
}

async function toggleInspect(next: boolean) {
  if (toggling.value) return
  toggling.value = true
  try {
    if (next) {
      const res = await inspectApi.start(threads.value, proxyRef.value)
      applyState(res.inspect)
      toast.success('巡检已启动')
      startLiveUpdates()
    } else {
      const res = await inspectApi.stop()
      applyState(res.inspect)
      toast.success('已请求停止巡检')
    }
  } catch {
    toast.error(next ? '启动巡检失败' : '停止巡检失败')
  } finally {
    toggling.value = false
  }
}

function startLiveUpdates() {
  stopLiveUpdates()
  const token = getAuthToken()
  if (!token) {
    startPolling()
    return
  }
  try {
    const baseUrl = String(import.meta.env.VITE_API_URL || '').replace(/\/$/, '')
    const source = new EventSource(`${baseUrl}/api/inspect/events?token=${encodeURIComponent(token)}`)
    source.onmessage = (event) => {
      try {
        applyState(JSON.parse(event.data) as InspectState)
      } catch {
        // ignore malformed event payload
      }
    }
    source.onerror = () => {
      stopLiveUpdates()
      startPolling()
    }
    eventSource.value = source
  } catch {
    startPolling()
  }
}

function stopLiveUpdates() {
  if (eventSource.value) {
    eventSource.value.close()
    eventSource.value = null
  }
}

function startPolling() {
  stopPolling()
  pollTimer.value = window.setInterval(async () => {
    await loadState(true)
    if (!running.value) stopPolling()
  }, 2000)
}

function stopPolling() {
  if (pollTimer.value) {
    window.clearInterval(pollTimer.value)
    pollTimer.value = null
  }
}

onMounted(async () => {
  await loadState()
  initProxyFromState()
  loadProxyGroups()
  startLiveUpdates()
})

onBeforeUnmount(() => {
  stopLiveUpdates()
  stopPolling()
})
</script>

<style scoped>
.inspect-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.inspect-controls {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 16px;
}

.inspect-threads {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--muted-foreground, #8b8b8b);
}

.inspect-threads-input {
  width: 56px;
  padding: 4px 8px;
  border: 1px solid var(--border, #d4d4d4);
  border-radius: 6px;
  background: var(--background, #fff);
  color: inherit;
  font-size: 12px;
}

.inspect-threads-input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.inspect-proxy-select,
.inspect-proxy-input {
  padding: 4px 8px;
  border: 1px solid var(--border, #d4d4d4);
  border-radius: 6px;
  background: var(--background, #fff);
  color: inherit;
  font-size: 12px;
}

.inspect-proxy-select {
  min-width: 104px;
}

.inspect-proxy-input {
  width: 220px;
}

.inspect-proxy-select:disabled,
.inspect-proxy-input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.inspect-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 12px;
  color: var(--muted-foreground, #8b8b8b);
}

.inspect-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid var(--border, #ebebeb);
  font-size: 12px;
  color: var(--muted-foreground, #8b8b8b);
}
</style>
