<template>
  <div class="flex items-center gap-2" :class="alignClass">
    <Button
      size="xs"
      variant="outline"
      root-class="w-14 justify-center"
      :disabled="item.is_demo"
      @click="emit('edit')"
    >
      编辑
    </Button>
    <FloatingActionMenu
      label="更多"
      :items="menuItems"
      :disabled="item.is_demo"
      align="right"
      size="sm"
      trigger-class="h-7 justify-center px-2 text-[11px]"
      :trigger-width="64"
      @select="handleSelect"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Button } from 'nanocat-ui'
import type { ActionMenuItem } from 'nanocat-ui'
import type { Account } from '@/api/accounts'
import FloatingActionMenu from './FloatingActionMenu.vue'
import { actionMenuGroups } from './menuItems'

const props = withDefaults(defineProps<{
  item: Account
  refreshing?: boolean
  refreshingOauth?: boolean
  resetting?: boolean
  align?: 'start' | 'end'
}>(), {
  refreshing: false,
  refreshingOauth: false,
  resetting: false,
  align: 'start',
})

const emit = defineEmits<{
  (e: 'edit'): void
  (e: 'toggle-enabled'): void
  (e: 'refresh-token'): void
  (e: 'refresh-oauth'): void
  (e: 'reauthorize'): void
  (e: 'reset-state'): void
  (e: 'remove'): void
}>()

const alignClass = computed(() => (
  props.align === 'end' ? 'justify-end' : 'justify-start'
))

const menuItems = computed<ActionMenuItem[]>(() => actionMenuGroups(
  [
    {
      key: 'refresh-token',
      label: props.refreshing ? '刷新中...' : '刷新账号信息和额度',
      disabled: props.refreshing,
    },
    {
      key: 'refresh-oauth',
      label: props.refreshingOauth ? '刷新令牌中...' : '刷新令牌(修复 401)',
      disabled: props.refreshingOauth,
    },
    {
      key: 'reauthorize',
      label: '重新授权',
    },
    {
      key: 'reset-state',
      label: props.resetting ? '重置中...' : '重置状态',
      disabled: props.resetting,
    },
  ],
  [
    {
      key: 'toggle-enabled',
      label: props.item.enabled ? '禁用账号' : '启用账号',
    },
  ],
  [
    {
      key: 'remove',
      label: '删除账号',
      danger: true,
    },
  ],
))

function handleSelect(key: string) {
  if (key === 'toggle-enabled') emit('toggle-enabled')
  if (key === 'refresh-token') emit('refresh-token')
  if (key === 'refresh-oauth') emit('refresh-oauth')
  if (key === 'reauthorize') emit('reauthorize')
  if (key === 'reset-state') emit('reset-state')
  if (key === 'remove') emit('remove')
}
</script>
