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
          <Checkbox :model-value="running" :disabled="toggling" @update:model-value="toggleInspect">
            {{ running ? '巡检运行中（取消勾选可停止）' : '开启巡检' }}
          </Checkbox>
          <div class="inspect-stats">
            <span>共 {{ stats.total }}</span>
            <span>删除 {{ stats.deleted }}</span>
            <span>命中 {{ stats.matched }}</span>
            <span>更新 {{ stats.synced }}</span>
            <span>失败 {{ stats.failed }}</span>
            <span>跳过 {{ stats.skipped }}</span>
          </div>
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
import { PagePanel, PanelHeader, RuntimeLogPanel, StateBadge, SurfaceBox, type RuntimeLogPanelLine } from '@/components/ai'
import { useToast } from '@/composables/useToast'

const toast = useToast()
const inspectState = ref<InspectState | null>(null)
const toggling = ref(false)
const eventSource = ref<EventSource | null>(null)
const pollTimer = ref<number | null>(null)

const running = computed(() => Boolean(inspectState.value?.enabled || inspectState.value?.stats?.running))
const stats = computed(() => ({
  total: inspectState.value?.stats?.total ?? 0,
  deleted: inspectState.value?.stats?.deleted ?? 0,
  matched: inspectState.value?.stats?.matched ?? 0,
  synced: inspectState.value?.stats?.synced ?? 0,
  failed: inspectState.value?.stats?.failed ?? 0,
  skipped: inspectState.value?.stats?.skipped ?? 0,
}))

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
      const res = await inspectApi.start()
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

.inspect-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 12px;
  color: var(--muted-foreground, #8b8b8b);
}
</style>
