<template>
  <div class="space-y-6">
    <PagePanel v-if="localSettings" class="space-y-5">
      <div class="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p class="ui-section-title">设置</p>
          <p class="mt-1 text-xs text-muted-foreground">按原版模块分组维护系统配置。</p>
        </div>
        <div class="flex flex-wrap gap-2">
          <Button size="sm" variant="outline" :disabled="settingsStore.isLoading || isSaving" @click="reloadSettings">
            {{ settingsStore.isLoading ? '刷新中...' : '刷新' }}
          </Button>
          <Button size="sm" variant="primary" :disabled="isSaving || !localSettings" @click="handleSave">
            {{ isSaving ? '保存中...' : '保存设置' }}
          </Button>
        </div>
      </div>

      <ConsoleSegmentedTabs v-model="activeSettingsTab" :options="settingsTabs" aria-label="设置分组" />

      <div v-if="activeSettingsTab === 'basic'" class="space-y-4">
        <SurfaceBox density="compact">
          <p class="text-xs leading-5 text-muted-foreground">
            管理员登录密钥继续从部署配置读取，不在此页面展示；如需分发给其他人，请到“用户密钥”创建普通用户密钥。
          </p>
        </SurfaceBox>

        <div class="grid gap-4 xl:grid-cols-3">
          <div class="space-y-4 xl:col-span-2">
            <FormSection title="基础配置">
              <div class="grid grid-cols-1 gap-3 md:grid-cols-2">
                <FormField label="账号刷新间隔">
                  <template #label-extra>
                    <HelpTip text="单位分钟，控制账号自动刷新频率。" />
                  </template>
                  <Input
                    :model-value="refreshAccountIntervalField.input.value"
                    type="number"
                    block
                    placeholder="5"
                    @update:model-value="refreshAccountIntervalField.update"
                  />
                </FormField>

                <FormField label="图片访问地址">
                  <template #label-extra>
                    <HelpTip text="用于生成图片结果的访问前缀地址。" />
                  </template>
                  <Input
                    v-model.trim="localSettings.base_url"
                    block
                    placeholder="https://example.com"
                  />
                </FormField>

                <FormField label="默认出口" class="md:col-span-2">
                  <template #label-extra>
                    <HelpTip text="账号个人代理、账号组代理优先于默认出口。可填写代理 URL、direct 或 group:代理组ID；完整选择可到代理管理维护。" />
                  </template>
                  <div class="flex flex-col gap-2 sm:flex-row">
                    <Input
                      v-model.trim="localSettings.proxy"
                      block
                      root-class="font-mono"
                      placeholder="http://127.0.0.1:7890"
                      @update:model-value="proxyTestResult = null"
                    />
                    <Button
                      size="sm"
                      variant="outline"
                      root-class="shrink-0"
                      :disabled="proxyBusy === 'test'"
                      @click="testDefaultProxy"
                    >
                      {{ proxyBusy === 'test' ? '测试中...' : '测试出口' }}
                    </Button>
                  </div>
                  <div v-if="proxyTestResult" class="mt-2 rounded-xl border border-border bg-background px-3 py-2 text-xs">
                    <p :class="proxyTestResult.ok ? 'text-emerald-600' : 'text-rose-600'">
                      {{ proxyTestResult.ok ? `出口可用：HTTP ${proxyTestResult.status}，${proxyTestResult.latency_ms} ms` : `出口不可用：${proxyTestResult.error || '未知错误'}` }}
                    </p>
                  </div>
                </FormField>

                <FormField label="图片自动清理">
                  <template #label-extra>
                    <HelpTip text="自动删除多少天前的本地图片。" />
                  </template>
                  <Input
                    :model-value="imageRetentionDaysField.input.value"
                    type="number"
                    block
                    placeholder="15"
                    @update:model-value="imageRetentionDaysField.update"
                  />
                </FormField>

                <FormField label="日志自动清理">
                  <template #label-extra>
                    <HelpTip text="自动删除多少天前的控制台调用日志，清理对象是 data/logs.jsonl。" />
                  </template>
                  <Input
                    :model-value="logRetentionDaysField.input.value"
                    type="number"
                    block
                    placeholder="30"
                    @update:model-value="logRetentionDaysField.update"
                  />
                </FormField>

                <FormField label="图片轮询超时">
                  <template #label-extra>
                    <HelpTip text="单位秒，等待上游图片结果的最长时间。" />
                  </template>
                  <Input
                    :model-value="imagePollTimeoutField.input.value"
                    type="number"
                    block
                    placeholder="120"
                    @update:model-value="imagePollTimeoutField.update"
                  />
                </FormField>

                <FormField label="上游流超时">
                  <template #label-extra>
                    <HelpTip text="单位秒，限制 ChatGPT 生图 SSE 流最长等待时间。" />
                  </template>
                  <Input
                    :model-value="imageStreamTimeoutField.input.value"
                    type="number"
                    block
                    placeholder="300"
                    @update:model-value="imageStreamTimeoutField.update"
                  />
                </FormField>

                <FormField label="单账号图片并发">
                  <template #label-extra>
                    <HelpTip text="限制每个账号同时处理的图片请求数量。" />
                  </template>
                  <Input
                    :model-value="imageAccountConcurrencyField.input.value"
                    type="number"
                    block
                    placeholder="3"
                    @update:model-value="imageAccountConcurrencyField.update"
                  />
                </FormField>

                <FormField label="超时继续等待">
                  <template #label-extra>
                    <HelpTip text="单位秒，图片超时后继续等待的额外时间。" />
                  </template>
                  <Input
                    :model-value="imageTimeoutRetryField.input.value"
                    type="number"
                    block
                    placeholder="30"
                    @update:model-value="imageTimeoutRetryField.update"
                  />
                </FormField>
              </div>
            </FormSection>

            <FormSection title="稳定代理 / Cloudflare 清障">
              <div class="rounded-xl border border-border bg-background px-3 py-3">
                <div class="grid grid-cols-2 gap-2 text-xs md:grid-cols-5">
                  <div
                    v-for="item in proxyRuntimeSummaryItems"
                    :key="item.label"
                    class="min-w-0 rounded-lg border border-border/70 bg-card px-2.5 py-2"
                  >
                    <p class="text-muted-foreground">{{ item.label }}</p>
                    <p class="mt-1 truncate font-medium text-foreground">{{ item.value }}</p>
                  </div>
                </div>
                <p v-if="proxyRuntimeStatus?.cached_clearance_hosts?.length" class="mt-2 break-all text-xs text-muted-foreground">
                  已缓存：{{ proxyRuntimeStatus.cached_clearance_hosts.join(' / ') }}
                </p>
              </div>

              <div class="settings-check-grid">
                <div class="settings-check-item">
                  <div class="settings-check-control">
                    <Checkbox v-model="localSettings.proxy_runtime.enabled">启用稳定代理运行时</Checkbox>
                    <HelpTip text="关闭时不会接管上游请求。" />
                  </div>
                </div>
                <div class="settings-check-item">
                  <div class="settings-check-control">
                    <Checkbox v-model="localSettings.proxy_runtime.clearance.enabled">启用 Cloudflare 清障</Checkbox>
                    <HelpTip text="只关闭清障时，可保留代理出站但不会注入 clearance。" />
                  </div>
                </div>
                <div class="settings-check-item">
                  <div class="settings-check-control">
                    <Checkbox v-model="localSettings.proxy_runtime.skip_ssl_verify">跳过上游 SSL 校验</Checkbox>
                    <HelpTip text="仅在代理或上游证书链异常时使用。" />
                  </div>
                </div>
                <div class="settings-check-item">
                  <div class="settings-check-control">
                    <Checkbox v-model="localSettings.proxy_runtime.clearance.warm_up_on_start">启动后预热 clearance</Checkbox>
                    <HelpTip text="服务启动后主动获取一次 clearance，减少首个请求等待。" />
                  </div>
                </div>
              </div>

              <div class="grid grid-cols-1 gap-3 md:grid-cols-2">
                <FormField label="出站方式">
                  <GroupedSelectMenu
                    v-model="localSettings.proxy_runtime.egress_mode"
                    :options="proxyRuntimeEgressOptions"
                    selected-indicator="none"
                    aria-label="稳定代理出站方式"
                    block
                  />
                </FormField>

                <FormField label="清障方式">
                  <GroupedSelectMenu
                    v-model="localSettings.proxy_runtime.clearance.mode"
                    :options="proxyClearanceModeOptions"
                    selected-indicator="none"
                    aria-label="Cloudflare 清障方式"
                    block
                  />
                </FormField>

                <FormField label="代理地址">
                  <template #label-extra>
                    <HelpTip text="Docker 清障编排默认使用 Privoxy HTTP 代理。" />
                  </template>
                  <Input
                    v-model.trim="localSettings.proxy_runtime.proxy_url"
                    block
                    root-class="font-mono"
                    placeholder="http://privoxy:8118"
                    @update:model-value="clearanceTestResult = null"
                  />
                </FormField>

                <FormField label="资源代理地址">
                  <Input
                    v-model.trim="localSettings.proxy_runtime.resource_proxy_url"
                    block
                    root-class="font-mono"
                    placeholder="留空则复用代理地址"
                    @update:model-value="clearanceTestResult = null"
                  />
                </FormField>

                <FormField
                  v-if="localSettings.proxy_runtime.clearance.mode === 'flaresolverr'"
                  label="FlareSolverr URL"
                  class="md:col-span-2"
                >
                  <Input
                    v-model.trim="localSettings.proxy_runtime.clearance.flaresolverr_url"
                    block
                    root-class="font-mono"
                    placeholder="http://flaresolverr:8191"
                    @update:model-value="clearanceTestResult = null"
                  />
                </FormField>

                <template v-if="localSettings.proxy_runtime.clearance.mode === 'manual'">
                  <FormField label="cf_clearance">
                    <Input
                      v-model.trim="localSettings.proxy_runtime.clearance.cf_clearance"
                      block
                      root-class="font-mono"
                      :placeholder="localSettings.proxy_runtime.clearance.has_cf_clearance ? '已保存，留空则沿用' : '手动填写 cf_clearance'"
                      @update:model-value="clearanceTestResult = null"
                    />
                  </FormField>

                  <FormField label="Cookie">
                    <Input
                      v-model.trim="localSettings.proxy_runtime.clearance.cf_cookies"
                      block
                      root-class="font-mono"
                      :placeholder="localSettings.proxy_runtime.clearance.has_cf_cookies ? '已保存，留空则沿用' : '可粘贴完整 Cookie'"
                      @update:model-value="clearanceTestResult = null"
                    />
                  </FormField>
                </template>

                <FormField label="User-Agent" class="md:col-span-2">
                  <Input
                    v-model.trim="localSettings.proxy_runtime.clearance.user_agent"
                    block
                    root-class="font-mono"
                    placeholder="Mozilla/5.0 ..."
                    @update:model-value="clearanceTestResult = null"
                  />
                </FormField>

                <FormField label="清障超时">
                  <template #label-extra>
                    <HelpTip text="单位秒。" />
                  </template>
                  <Input
                    :model-value="clearanceTimeoutField.input.value"
                    type="number"
                    block
                    placeholder="60"
                    @update:model-value="clearanceTimeoutField.update"
                  />
                </FormField>

                <FormField label="缓存刷新间隔">
                  <template #label-extra>
                    <HelpTip text="单位秒，最小 60。" />
                  </template>
                  <Input
                    :model-value="clearanceRefreshIntervalField.input.value"
                    type="number"
                    block
                    placeholder="3600"
                    @update:model-value="clearanceRefreshIntervalField.update"
                  />
                </FormField>

                <FormField label="测试目标" class="md:col-span-2">
                  <div class="flex flex-col gap-2 sm:flex-row">
                    <Input
                      v-model.trim="clearanceTestTarget"
                      block
                      root-class="font-mono"
                      placeholder="https://chatgpt.com"
                    />
                    <Button
                      size="sm"
                      variant="outline"
                      root-class="shrink-0"
                      :disabled="proxyRuntimeLoading"
                      @click="loadProxyRuntimeStatus(false)"
                    >
                      {{ proxyRuntimeLoading ? '刷新中...' : '刷新状态' }}
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      root-class="shrink-0"
                      :disabled="proxyRuntimeTesting"
                      @click="testProxyClearance"
                    >
                      {{ proxyRuntimeTesting ? '测试中...' : '测试清障' }}
                    </Button>
                  </div>
                </FormField>
              </div>

              <div v-if="clearanceTestResult" class="rounded-xl border border-border bg-background px-3 py-2 text-xs">
                <p :class="clearanceTestResult.ok ? 'text-emerald-600' : 'text-rose-600'">
                  {{ clearanceTestResult.ok ? `清障可用：${clearanceTestResult.latency_ms} ms` : `清障不可用：${clearanceTestResult.error || '未知错误'}` }}
                </p>
                <p v-if="clearanceTestResult.user_agent" class="mt-1 break-all text-muted-foreground">
                  User-Agent：{{ clearanceTestResult.user_agent }}
                </p>
              </div>
            </FormSection>

            <FormSection title="全局附加指令">
              <FormField label="全局系统提示词">
                <template #label-extra>
                  <HelpTip text="每次请求都会作为 system 消息注入。" />
                </template>
                <textarea
                  v-model="localSettings.global_system_prompt"
                  rows="5"
                  class="ui-textarea-sm"
                  placeholder="例如：先判断用户提示词是否合规；遇到违法、色情、暴力、仇恨等请求时拒绝回答。"
                ></textarea>
              </FormField>

              <FormField label="敏感词">
                <textarea
                  v-model="sensitiveWordsText"
                  rows="5"
                  class="ui-textarea-sm"
                  placeholder="一行一个，命中即拒绝"
                ></textarea>
              </FormField>
            </FormSection>
          </div>

          <div class="space-y-4">
            <FormSection title="账号策略">
              <div class="settings-check-grid settings-check-grid--single">
                <div class="settings-check-item">
                  <div class="settings-check-control">
                    <Checkbox v-model="localSettings.auto_remove_invalid_accounts">自动移除异常账号</Checkbox>
                    <HelpTip text="确认鉴权无效的账号会进入异常处理；开启后直接移除，关闭后保留异常状态。" />
                  </div>
                </div>
                <div class="settings-check-item">
                  <div class="settings-check-control">
                    <Checkbox v-model="localSettings.auto_remove_rate_limited_accounts">自动移除额度耗尽账号</Checkbox>
                    <HelpTip text="只有远程明确确认图片额度为 0 时才会处理，代理错误、断流或上游 429 不会删除账号。" />
                  </div>
                </div>
              </div>
            </FormSection>

            <FormSection title="图片确认">
              <div class="settings-check-grid settings-check-grid--single">
                <div class="settings-check-item">
                  <div class="settings-check-control">
                    <Checkbox v-model="localSettings.image_settle_enabled">图片二次确认机制</Checkbox>
                    <HelpTip text="找到图片结果后再等待指定秒数复查一次，减少结果尚未稳定时提前返回。" />
                  </div>
                </div>
              </div>
              <FormField label="二次确认等待（秒）">
                <Input
                  :model-value="imageSettleSecondsField.input.value"
                  type="number"
                  block
                  placeholder="5"
                  :disabled="!localSettings.image_settle_enabled"
                  @update:model-value="imageSettleSecondsField.update"
                />
              </FormField>
            </FormSection>

            <FormSection title="控制台日志级别">
              <div class="settings-check-grid settings-check-grid--single mt-3">
                <div
                  v-for="level in logLevelOptions"
                  :key="level"
                  class="settings-check-item"
                >
                  <div class="settings-check-control">
                    <Checkbox
                      :model-value="localSettings.log_levels.includes(level)"
                      @update:model-value="setLogLevel(level, Boolean($event))"
                    >
                      {{ level }}
                    </Checkbox>
                    <HelpTip v-if="level === 'debug'" text="不选择任何级别时使用默认 info / warning / error。" />
                  </div>
                </div>
              </div>
            </FormSection>
          </div>
        </div>
      </div>

      <div v-else-if="activeSettingsTab === 'image-errors'" class="space-y-4">
        <FormSection title="图片错误提示">
          <div class="settings-check-grid settings-check-grid--single">
            <div class="settings-check-item">
              <div class="settings-check-control">
                <Checkbox v-model="localSettings.image_error_friendly_enabled">启用图片错误提示友好化</Checkbox>
                <HelpTip text="关闭时保持原始错误返回；开启后按下方文案转换上游断流、轮询超时、额度耗尽等图片错误。" />
              </div>
            </div>
          </div>
        </FormSection>

        <FormSection title="自定义错误文案">
          <div class="grid grid-cols-1 gap-3 md:grid-cols-2">
            <FormField
              v-for="item in imageErrorMessageFields"
              :key="item.key"
              :label="item.label"
            >
              <template v-if="item.help" #label-extra>
                <HelpTip :text="item.help" />
              </template>
              <textarea
                v-model="localSettings.image_error_messages[item.key]"
                rows="3"
                class="ui-textarea-sm"
                :placeholder="item.placeholder"
                :disabled="!localSettings.image_error_friendly_enabled"
              ></textarea>
            </FormField>
          </div>
        </FormSection>
      </div>

      <div v-else-if="activeSettingsTab === 'storage'" class="grid gap-4 xl:grid-cols-3">
        <FormSection title="图片存储" class="xl:col-span-2">
          <div class="settings-check-grid settings-check-grid--single">
            <div class="settings-check-item">
              <Checkbox v-model="localSettings.image_storage.enabled">启用 WebDAV 图片存储</Checkbox>
            </div>
          </div>

          <FormField label="存储模式">
            <div class="w-full">
              <GroupedSelectMenu
                v-model="localSettings.image_storage.mode"
                :options="imageStorageModeOptions"
                selected-indicator="none"
                aria-label="图片存储模式"
                block
              />
            </div>
          </FormField>

          <FormField label="WebDAV URL">
            <Input v-model.trim="localSettings.image_storage.webdav_url" block placeholder="https://example.com/dav" />
          </FormField>

          <div class="grid grid-cols-1 gap-2.5 md:grid-cols-2">
            <FormField label="用户名">
              <Input v-model.trim="localSettings.image_storage.webdav_username" block />
            </FormField>

            <FormField label="密码">
              <Input v-model="localSettings.image_storage.webdav_password" type="password" block />
            </FormField>
          </div>

          <FormField label="根路径">
            <Input v-model.trim="localSettings.image_storage.webdav_root_path" block placeholder="chatgpt2api/images" />
          </FormField>

          <FormField label="公开访问前缀">
            <Input v-model.trim="localSettings.image_storage.public_base_url" block placeholder="https://cdn.example.com/images" />
          </FormField>

          <div class="flex flex-wrap items-center gap-2">
            <Button size="xs" variant="outline" :disabled="imageStorageBusy === 'test'" @click="testImageStorageConnection">
              {{ imageStorageBusy === 'test' ? '测试中...' : '测试 WebDAV' }}
            </Button>
            <Button size="xs" variant="outline" :disabled="imageStorageBusy === 'sync'" @click="syncImageStorageFiles">
              {{ imageStorageBusy === 'sync' ? '同步中...' : '全量同步' }}
            </Button>
          </div>

          <div v-if="imageStorageTestResult" class="rounded-xl border border-border bg-background px-3 py-2 text-xs">
            <p :class="imageStorageTestResult.ok ? 'text-emerald-600' : 'text-slate-600'">
              {{ imageStorageTestResult.ok ? 'WebDAV 可用' : 'WebDAV 不可用' }}
              <span v-if="imageStorageTestResult.status"> · HTTP {{ imageStorageTestResult.status }}</span>
            </p>
            <p v-if="imageStorageTestResult.error" class="mt-1 break-all text-slate-600">{{ imageStorageTestResult.error }}</p>
          </div>
        </FormSection>

        <FormSection title="AI 审核">
          <div class="settings-check-grid settings-check-grid--single">
            <div class="settings-check-item">
              <Checkbox v-model="localSettings.ai_review.enabled">启用 AI 审核</Checkbox>
            </div>
          </div>

          <FormField label="Base URL">
            <Input v-model.trim="localSettings.ai_review.base_url" block placeholder="https://api.openai.com" />
          </FormField>

          <FormField label="API Key">
            <Input v-model="localSettings.ai_review.api_key" type="password" block placeholder="sk-..." />
          </FormField>

          <FormField label="Model">
            <Input v-model.trim="localSettings.ai_review.model" block placeholder="gpt-5.4-mini" />
          </FormField>

          <FormField label="审核提示词">
            <textarea
              v-model="localSettings.ai_review.prompt"
              rows="5"
              class="ui-textarea-sm"
              placeholder="判断用户请求是否允许。只回答 ALLOW 或 REJECT。"
            ></textarea>
          </FormField>
        </FormSection>
      </div>

      <div v-else-if="activeSettingsTab === 'backup'" class="space-y-4">
        <FormSection title="R2 备份管理">
          <div class="settings-check-grid">
            <div class="settings-check-item">
              <Checkbox v-model="localSettings.backup.enabled">启用定时备份</Checkbox>
            </div>
            <div class="settings-check-item">
              <Checkbox v-model="localSettings.backup.encrypt">启用备份加密</Checkbox>
            </div>
          </div>

          <div class="grid grid-cols-1 gap-2.5 md:grid-cols-2">
            <FormField label="Cloudflare Account ID">
              <Input v-model.trim="localSettings.backup.account_id" block />
            </FormField>

            <FormField label="Bucket 名称">
              <Input v-model.trim="localSettings.backup.bucket" block />
            </FormField>
          </div>

          <div class="grid grid-cols-1 gap-2.5 md:grid-cols-2">
            <FormField label="Access Key ID">
              <Input v-model.trim="localSettings.backup.access_key_id" block />
            </FormField>

            <FormField label="Secret Access Key">
              <Input v-model="localSettings.backup.secret_access_key" type="password" block />
            </FormField>
          </div>

          <div class="grid grid-cols-1 gap-2.5 md:grid-cols-2">
            <FormField label="备份前缀">
              <Input v-model.trim="localSettings.backup.prefix" block placeholder="backups" />
            </FormField>

            <FormField label="保留份数">
              <Input
                :model-value="backupRotationKeepField.input.value"
                type="number"
                block
                @update:model-value="backupRotationKeepField.update"
              />
            </FormField>
          </div>

          <FormField label="备份间隔（分钟）">
            <Input
              :model-value="backupIntervalMinutesField.input.value"
              type="number"
              block
              @update:model-value="backupIntervalMinutesField.update"
            />
          </FormField>

          <FormField label="加密口令">
            <Input v-model="localSettings.backup.passphrase" type="password" block placeholder="留空" />
          </FormField>

          <div class="space-y-2">
            <p class="text-xs font-medium text-foreground">备份内容</p>
            <div class="settings-check-grid">
              <div
                v-for="item in backupIncludeOptions"
                :key="item.value"
                class="settings-check-item"
              >
                <Checkbox v-model="localSettings.backup.include[item.value]">{{ item.label }}</Checkbox>
              </div>
            </div>
          </div>

          <div class="flex flex-wrap items-center gap-2">
            <Button size="xs" variant="outline" :disabled="backupBusy === 'test'" @click="testBackupConnection">
              {{ backupBusy === 'test' ? '测试中...' : '测试连接' }}
            </Button>
            <Button size="xs" variant="outline" :disabled="backupBusy === 'run' || backupState?.running" @click="runBackupNow">
              {{ backupBusy === 'run' || backupState?.running ? '备份中...' : '立即备份' }}
            </Button>
            <Button size="xs" variant="outline" :disabled="backupLoading" @click="loadBackups">
              {{ backupLoading ? '加载中...' : '刷新历史' }}
            </Button>
          </div>

          <div v-if="backupTestResult" class="rounded-xl border border-border bg-background px-3 py-2 text-xs">
            <p :class="backupTestResult.ok ? 'text-emerald-600' : 'text-rose-600'">
              {{ backupTestResult.ok ? '备份连接可用' : '备份连接不可用' }}
              <span v-if="backupTestResult.status"> · HTTP {{ backupTestResult.status }}</span>
            </p>
            <p v-if="backupTestResult.error" class="mt-1 break-all text-rose-600">{{ backupTestResult.error }}</p>
          </div>

          <div class="rounded-xl border border-border bg-background px-3 py-3 text-xs">
            <div class="grid grid-cols-2 gap-2 text-muted-foreground">
              <span>最近状态</span>
              <span class="text-right text-foreground">{{ backupStatusText }}</span>
              <span>最近开始</span>
              <span class="text-right text-foreground">{{ formatDateTime(backupState?.last_started_at) }}</span>
              <span>最近完成</span>
              <span class="text-right text-foreground">{{ formatDateTime(backupState?.last_finished_at) }}</span>
              <span>最近对象</span>
              <span class="break-all text-right font-mono text-foreground">{{ backupState?.last_object_key || '-' }}</span>
              <span>最近错误</span>
              <span class="break-all text-right text-rose-600">{{ backupState?.last_error || '-' }}</span>
            </div>
          </div>

          <div v-if="backupItems.length > 0" class="space-y-2">
            <div
              v-for="item in backupItems.slice(0, 5)"
              :key="item.key"
              class="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-border bg-card px-3 py-2 text-xs"
            >
              <div class="min-w-0">
                <p class="truncate font-medium text-foreground">{{ item.name || item.key }}</p>
                <p class="mt-1 text-muted-foreground">{{ formatBytes(item.size_bytes ?? item.size ?? 0) }} · {{ item.last_modified || '-' }}</p>
              </div>
              <Button size="xs" variant="outline" root-class="text-rose-600" :disabled="backupBusy === item.key" @click="deleteBackupItem(item)">
                删除
              </Button>
            </div>
          </div>
        </FormSection>
      </div>

      <div v-else-if="activeSettingsTab === 'canvas'" class="max-w-3xl">
        <FormSection title="画布入口" subtitle="开启后顶部导航会显示无限画布入口，并自动带上当前接口地址和密钥。">
          <div class="settings-check-grid settings-check-grid--single">
            <div class="settings-check-item">
              <Checkbox v-model="localSettings.third_party_apps.infinite_canvas.enabled">启用无限画布入口</Checkbox>
            </div>
          </div>
          <FormField label="无限画布地址">
            <Input
              v-model.trim="localSettings.third_party_apps.infinite_canvas.url"
              block
              placeholder="https://canvas.best"
            />
          </FormField>
        </FormSection>
      </div>

      <div v-else-if="activeSettingsTab === 'register-postprocess'" class="max-w-3xl">
        <FormSection title="注册后自动入库 sub2api" subtitle="outlook007 渠道账号注册成功后，自动 join 空间 → 转 sub2api 格式 → 推送到 sub2api。">
          <div class="settings-check-grid settings-check-grid--single">
            <div class="settings-check-item">
              <Checkbox v-model="localSettings.register_postprocess.enabled">启用注册后自动入库</Checkbox>
            </div>
            <div class="settings-check-item">
              <Checkbox v-model="localSettings.register_postprocess.verify_chat_access">join 后验证可对话再推送</Checkbox>
            </div>
          </div>
          <FormField label="空间 ID (workspace_id)">
            <Input
              v-model.trim="localSettings.register_postprocess.workspace_id"
              block
              placeholder="631e1603-06cf-4f0b-b79b-d09fbfcfe98d"
            />
          </FormField>
          <FormField label="sub2api 地址">
            <Input
              v-model.trim="localSettings.register_postprocess.sub2api_base_url"
              block
              placeholder="http://15.204.89.156:8080"
            />
          </FormField>
          <FormField label="sub2api API 密钥 (x-api-key)">
            <Input
              v-model.trim="localSettings.register_postprocess.sub2api_api_key"
              block
              placeholder="admin-xxxxxxxx"
            />
          </FormField>
          <FormField label="分组 ID (group_ids，逗号分隔)">
            <Input
              v-model.trim="registerPostprocessGroupIdsText"
              block
              placeholder="2"
            />
          </FormField>
        </FormSection>
      </div>

      <div v-else-if="activeSettingsTab === 'api-docs'" class="space-y-4">
        <FormSection title="接口接入" subtitle="第三方应用按 OpenAI 兼容接口接入，使用同一套 Bearer 鉴权。">
          <div class="grid gap-3 md:grid-cols-2">
            <SurfaceBox density="compact">
              <p class="text-xs text-muted-foreground">服务地址</p>
              <p class="mt-1 break-all font-mono text-xs text-foreground">{{ serviceBaseUrl }}</p>
            </SurfaceBox>
            <SurfaceBox density="compact">
              <p class="text-xs text-muted-foreground">Base URL（OpenAI）</p>
              <p class="mt-1 break-all font-mono text-xs text-foreground">{{ openAIBaseUrl }}</p>
            </SurfaceBox>
            <SurfaceBox density="compact">
              <p class="text-xs text-muted-foreground">API Key</p>
              <p class="mt-1 break-all font-mono text-xs text-foreground">{{ currentApiKey }}</p>
            </SurfaceBox>
            <SurfaceBox density="compact">
              <p class="text-xs text-muted-foreground">请求头</p>
              <p class="mt-1 break-all font-mono text-xs text-foreground">Authorization: Bearer {{ currentApiKey }}</p>
            </SurfaceBox>
          </div>
        </FormSection>

        <FormSection title="常用接口">
          <div class="space-y-2">
            <details
              v-for="item in apiDocItems"
              :key="item.path"
              class="rounded-xl border border-border bg-card px-4 py-3"
            >
              <summary class="flex cursor-pointer list-none items-center justify-between gap-3">
                <span class="min-w-0">
                  <span class="block text-sm font-medium text-foreground">{{ item.title }}</span>
                  <span class="mt-1 block truncate font-mono text-xs text-muted-foreground">{{ item.method }} {{ item.path }}</span>
                </span>
                <span class="text-xs text-muted-foreground">展开</span>
              </summary>
              <div class="mt-3 space-y-2">
                <p class="text-xs leading-5 text-muted-foreground">{{ item.description }}</p>
                <pre class="overflow-auto whitespace-pre-wrap break-all rounded-xl bg-zinc-950 px-3 py-3 text-xs leading-5 text-zinc-100">{{ item.example }}</pre>
              </div>
            </details>
          </div>
        </FormSection>
      </div>
    </PagePanel>

    <PagePanel v-if="localSettings && activeSettingsTab === 'keys'" class="space-y-4">
      <div class="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p class="ui-section-title">用户密钥管理</p>
          <p class="mt-1 text-xs text-muted-foreground">
            创建给普通用户使用的调用密钥；普通用户登录后只进入对话画图页。
          </p>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <Button size="sm" variant="outline" :disabled="userKeysLoading" @click="loadUserKeys">
            {{ userKeysLoading ? '刷新中...' : '刷新密钥' }}
          </Button>
          <Button size="sm" variant="primary" :disabled="userKeyBusy === 'create'" @click="openUserKeyCreateModal">
            创建用户密钥
          </Button>
        </div>
      </div>

      <div
        v-if="newUserKey"
        class="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900"
      >
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div class="min-w-0">
            <p class="font-medium">新密钥只展示一次，请现在复制保存。</p>
            <p class="mt-2 break-all font-mono text-xs">{{ newUserKey }}</p>
          </div>
          <Button size="xs" variant="outline" root-class="shrink-0 border-emerald-200 bg-white text-emerald-700" @click="copyUserKey(newUserKey)">
            复制
          </Button>
        </div>
      </div>

      <PageLoadingState
        v-if="userKeysLoading"
        compact
        dashed
        title="正在加载用户密钥"
        description="读取普通用户密钥列表。"
      />
      <StateBlock v-else-if="userKeys.length === 0" compact dashed>
        暂无普通用户密钥。创建后可以分发给只需要画图入口的用户。
      </StateBlock>
      <div v-else class="space-y-2">
        <div
          v-for="item in userKeys"
          :key="item.id"
          class="flex flex-col gap-3 rounded-xl border border-border bg-card px-4 py-3 md:flex-row md:items-center md:justify-between"
        >
          <div class="min-w-0">
            <div class="flex flex-wrap items-center gap-2">
              <p class="truncate text-sm font-medium text-foreground">{{ item.name || '普通用户' }}</p>
              <span
                class="rounded-md px-2 py-0.5 text-xs"
                :class="item.enabled ? 'bg-emerald-50 text-emerald-700' : 'bg-secondary text-muted-foreground'"
              >
                {{ item.enabled ? '已启用' : '已禁用' }}
              </span>
            </div>
            <p class="mt-1 text-xs text-muted-foreground">
              创建 {{ formatDateTime(item.created_at) }} · 最近使用 {{ formatDateTime(item.last_used_at) }}
            </p>
          </div>
          <div class="flex flex-wrap items-center gap-2">
            <Button
              size="xs"
              variant="outline"
              :disabled="userKeyBusy === item.id"
              @click="openUserKeyEditModal(item)"
            >
              编辑
            </Button>
            <Button
              size="xs"
              variant="outline"
              :disabled="userKeyBusy === item.id"
              @click="toggleUserKey(item)"
            >
              {{ item.enabled ? '禁用' : '启用' }}
            </Button>
            <Button
              size="xs"
              variant="outline"
              root-class="text-rose-600"
              :disabled="userKeyBusy === item.id"
              @click="deleteUserKey(item)"
            >
              删除
            </Button>
          </div>
        </div>
      </div>
    </PagePanel>

    <PagePanel v-if="localSettings && (activeSettingsTab === 'cpa' || activeSettingsTab === 'sub2api')" class="space-y-4">
      <div class="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p class="ui-section-title">{{ activeSettingsTab === 'cpa' ? 'CPA' : 'Sub2API' }}</p>
          <p class="mt-1 text-xs text-muted-foreground">
            账号管理页的远程导入会读取这里保存的连接。
          </p>
        </div>
        <Button size="sm" variant="outline" :disabled="externalSourcesLoading" @click="loadExternalSources">
          {{ externalSourcesLoading ? '刷新中...' : '刷新连接' }}
        </Button>
      </div>

      <div class="grid gap-4">
        <div v-if="activeSettingsTab === 'cpa'" class="rounded-xl border border-border bg-card p-4">
          <div class="flex items-center justify-between gap-3">
            <div>
              <p class="text-sm font-semibold text-foreground">CPA 连接管理</p>
              <p class="mt-1 text-xs text-muted-foreground">保存 CLIProxyAPI 地址和管理密钥，供远程 CPA 导入使用。</p>
            </div>
            <div class="flex shrink-0 items-center gap-2">
              <span class="text-xs text-muted-foreground">{{ cpaPools.length }} 个连接</span>
              <Button size="xs" variant="outline" :disabled="savingExternalSource === 'cpa'" @click="openCPAModal()">
                新增
              </Button>
            </div>
          </div>

          <div class="mt-4 space-y-2">
            <div
              v-for="pool in cpaPools"
              :key="pool.id"
              class="rounded-xl border border-border bg-background px-3 py-2 text-xs"
            >
              <div class="flex flex-wrap items-start justify-between gap-2">
                <div class="min-w-0">
                  <p class="truncate font-medium text-foreground">{{ pool.name || pool.id }}</p>
                  <p class="mt-1 truncate font-mono text-muted-foreground">{{ pool.base_url }}</p>
                </div>
                <div class="flex gap-1.5">
                  <Button size="xs" variant="outline" root-class="w-12 justify-center" :disabled="testingExternalSource === pool.id" @click="testCPAPool(pool)">
                    {{ testingExternalSource === pool.id ? '测试中' : '测试' }}
                  </Button>
                  <Button size="xs" variant="outline" root-class="w-12 justify-center" @click="editCPAPool(pool)">编辑</Button>
                  <Button size="xs" variant="outline" root-class="w-12 justify-center text-rose-600" :disabled="savingExternalSource === pool.id" @click="deleteCPAPool(pool)">
                    删除
                  </Button>
                </div>
              </div>
            </div>
            <StateBlock v-if="!cpaLoading && cpaPools.length === 0" tag="p" compact dashed>
              暂无 CPA 连接。
            </StateBlock>
          </div>
        </div>

        <div v-if="activeSettingsTab === 'sub2api'" class="rounded-xl border border-border bg-card p-4">
          <div class="flex items-center justify-between gap-3">
            <div>
              <p class="text-sm font-semibold text-foreground">Sub2API 连接管理</p>
              <p class="mt-1 text-xs text-muted-foreground">保存 Sub2API 服务器，用于读取 OpenAI OAuth 账号并导入本地号池。</p>
            </div>
            <div class="flex shrink-0 items-center gap-2">
              <span class="text-xs text-muted-foreground">{{ sub2apiServers.length }} 个连接</span>
              <Button size="xs" variant="outline" :disabled="savingExternalSource === 'sub2api'" @click="openSub2APIModal()">
                新增
              </Button>
            </div>
          </div>

          <div class="mt-4 space-y-2">
            <div
              v-for="server in sub2apiServers"
              :key="server.id"
              class="rounded-xl border border-border bg-background px-3 py-2 text-xs"
            >
              <div class="flex flex-wrap items-start justify-between gap-2">
                <div class="min-w-0">
                  <p class="truncate font-medium text-foreground">{{ server.name || server.id }}</p>
                  <p class="mt-1 truncate font-mono text-muted-foreground">{{ server.base_url }}</p>
                  <p class="mt-1 text-muted-foreground">
                    {{ server.email || '未填邮箱' }} · {{ server.has_api_key ? '已配置 API Key' : '未配置 API Key' }}
                    <span v-if="server.group_id"> · 分组 {{ server.group_id }}</span>
                  </p>
                </div>
                <div class="flex flex-wrap justify-end gap-1.5">
                  <Button size="xs" variant="outline" root-class="w-12 justify-center" :disabled="testingExternalSource === server.id" @click="testSub2APIServer(server)">
                    {{ testingExternalSource === server.id ? '测试中' : '测试' }}
                  </Button>
                  <Button size="xs" variant="outline" root-class="w-16 justify-center" :disabled="sub2apiGroupsLoadingId === server.id" @click="loadSub2APIGroups(server)">
                    {{ sub2apiGroupsLoadingId === server.id ? '读取中' : '读分组' }}
                  </Button>
                  <Button size="xs" variant="outline" root-class="w-12 justify-center" @click="editSub2APIServer(server)">编辑</Button>
                  <Button size="xs" variant="outline" root-class="w-12 justify-center text-rose-600" :disabled="savingExternalSource === server.id" @click="deleteSub2APIServer(server)">
                    删除
                  </Button>
                </div>
              </div>

              <div v-if="sub2apiGroups[server.id]?.length" class="mt-2 flex flex-wrap gap-1.5">
                <button
                  v-for="group in sub2apiGroups[server.id]"
                  :key="group.id"
                  type="button"
                  class="rounded-md border border-border bg-card px-2 py-1 text-xs text-muted-foreground hover:text-foreground"
                  @click="useSub2APIGroup(server, group.id)"
                >
                  {{ group.name || group.id }} · {{ group.active_account_count }}/{{ group.account_count }}
                </button>
              </div>
            </div>
            <StateBlock v-if="!sub2apiLoading && sub2apiServers.length === 0" tag="p" compact dashed>
              暂无 Sub2API 连接。
            </StateBlock>
          </div>
        </div>
      </div>
    </PagePanel>

    <PagePanel v-if="!localSettings" class="py-10 text-center text-sm text-muted-foreground">
      <PageLoadingState
        v-if="settingsStore.isLoading"
        title="正在加载设置"
        description="读取系统配置、存储配置和外部连接。"
      />
      <StateBlock
        v-else
        title="设置加载失败"
        :description="settingsLoadError || '未获取到系统配置，请重新加载。'"
      >
        <Button size="sm" variant="outline" root-class="mt-4" @click="reloadSettings">
          重新加载
        </Button>
      </StateBlock>
    </PagePanel>

    <ModalShell
      :open="userKeyModal === 'create'"
      max-width="34rem"
      :z-index="130"
      close-on-backdrop
      @close="closeUserKeyModal"
    >
      <ModalHeader
        title="创建用户密钥"
        subtitle="名称只是备注；创建后会生成一条只展示一次的原始密钥。"
        :close-disabled="userKeyBusy === 'create'"
        :bordered="false"
        @close="closeUserKeyModal"
      />
      <ModalBody class="space-y-3">
        <FormField label="名称">
          <Input v-model.trim="userKeyForm.name" block placeholder="例如：运营画图账号" />
        </FormField>
      </ModalBody>
      <ModalFooter :bordered="false">
        <Button size="sm" variant="outline" :disabled="userKeyBusy === 'create'" @click="closeUserKeyModal">取消</Button>
        <Button size="sm" variant="primary" :disabled="userKeyBusy === 'create'" @click="createUserKey">
          {{ userKeyBusy === 'create' ? '创建中...' : '创建' }}
        </Button>
      </ModalFooter>
    </ModalShell>

    <ModalShell
      :open="userKeyModal === 'edit'"
      max-width="34rem"
      :z-index="130"
      close-on-backdrop
      @close="closeUserKeyModal"
    >
      <ModalHeader
        title="编辑用户密钥"
        subtitle="可以修改备注名称；填写新的专用密钥会让旧密钥失效。"
        :close-disabled="Boolean(editingUserKey && userKeyBusy === editingUserKey.id)"
        :bordered="false"
        @close="closeUserKeyModal"
      />
      <ModalBody class="space-y-3">
        <FormField label="名称">
          <Input v-model.trim="userKeyForm.name" block placeholder="例如：运营画图账号" />
        </FormField>
        <FormField label="新的专用密钥（可选）">
          <Input v-model.trim="userKeyForm.key" block root-class="font-mono" placeholder="留空则不修改当前密钥" />
        </FormField>
      </ModalBody>
      <ModalFooter :bordered="false">
        <Button size="sm" variant="outline" :disabled="Boolean(editingUserKey && userKeyBusy === editingUserKey.id)" @click="closeUserKeyModal">取消</Button>
        <Button size="sm" variant="primary" :disabled="Boolean(editingUserKey && userKeyBusy === editingUserKey.id)" @click="updateUserKey">
          {{ editingUserKey && userKeyBusy === editingUserKey.id ? '保存中...' : '保存' }}
        </Button>
      </ModalFooter>
    </ModalShell>

    <ModalShell
      :open="externalSourceModal === 'cpa'"
      max-width="38rem"
      :z-index="130"
      close-on-backdrop
      @close="closeExternalSourceModal"
    >
      <ModalHeader
        :title="editingCPAPoolId ? '编辑 CPA 连接' : '新增 CPA 连接'"
        subtitle="用于账号管理里的远程 CPA 导入。"
        :close-disabled="savingExternalSource === 'cpa'"
        :bordered="false"
        @close="closeExternalSourceModal"
      />
      <ModalBody class="space-y-3">
        <div class="grid gap-3 md:grid-cols-2">
          <FormField label="名称">
            <Input v-model.trim="cpaForm.name" block placeholder="主 CPA" />
          </FormField>
          <FormField label="CPA 地址">
            <Input v-model.trim="cpaForm.base_url" block placeholder="http://your-cpa-host:8317" />
          </FormField>
        </div>
        <FormField label="管理密钥">
          <Input v-model="cpaForm.secret_key" type="password" block :placeholder="editingCPAPoolId ? '留空则不修改密钥' : 'CPA 管理密钥'" />
        </FormField>
      </ModalBody>
      <ModalFooter :bordered="false">
        <Button size="sm" variant="outline" :disabled="savingExternalSource === 'cpa'" @click="closeExternalSourceModal">取消</Button>
        <Button size="sm" variant="primary" :disabled="savingExternalSource === 'cpa'" @click="saveCPAPool">
          {{ savingExternalSource === 'cpa' ? '保存中...' : '保存' }}
        </Button>
      </ModalFooter>
    </ModalShell>

    <ModalShell
      :open="externalSourceModal === 'sub2api'"
      max-width="42rem"
      :z-index="130"
      close-on-backdrop
      @close="closeExternalSourceModal"
    >
      <ModalHeader
        :title="editingSub2APIId ? '编辑 Sub2API 连接' : '新增 Sub2API 连接'"
        subtitle="用于账号管理里的 Sub2API 远程导入。"
        :close-disabled="savingExternalSource === 'sub2api'"
        :bordered="false"
        @close="closeExternalSourceModal"
      />
      <ModalBody class="space-y-3">
        <div class="grid gap-3 md:grid-cols-2">
          <FormField label="名称">
            <Input v-model.trim="sub2apiForm.name" block placeholder="自建 Sub2API" />
          </FormField>
          <FormField label="Sub2API 地址">
            <Input v-model.trim="sub2apiForm.base_url" block placeholder="http://your-sub2api-host:8080" />
          </FormField>
          <FormField label="管理员邮箱">
            <Input v-model.trim="sub2apiForm.email" block placeholder="admin@example.com" />
          </FormField>
          <FormField label="密码">
            <Input v-model="sub2apiForm.password" type="password" block :placeholder="editingSub2APIId ? '留空则不修改密码' : '管理员密码'" />
          </FormField>
          <FormField label="Admin API Key">
            <Input v-model="sub2apiForm.api_key" type="password" block :placeholder="editingSub2APIId ? '留空则不修改密钥' : '可替代邮箱密码'" />
          </FormField>
          <FormField label="默认分组 ID">
            <Input v-model.trim="sub2apiForm.group_id" block placeholder="可选" />
          </FormField>
        </div>
      </ModalBody>
      <ModalFooter :bordered="false">
        <Button size="sm" variant="outline" :disabled="savingExternalSource === 'sub2api'" @click="closeExternalSourceModal">取消</Button>
        <Button size="sm" variant="primary" :disabled="savingExternalSource === 'sub2api'" @click="saveSub2APIServer">
          {{ savingExternalSource === 'sub2api' ? '保存中...' : '保存' }}
        </Button>
      </ModalFooter>
    </ModalShell>
  </div>
</template>

<script setup lang="ts">
import { computed, onActivated, onMounted, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { Button, Checkbox, FormField, FormSection, HelpTip, Input } from 'nanocat-ui'
import GroupedSelectMenu from '@/components/ui/GroupedSelectMenu.vue'
import { accountImportsApi, type CPAPool, type Sub2APIRemoteGroup, type Sub2APIServer } from '@/api/accountImports'
import {
  normalizeProxyRuntime,
  prepareSettingsForEdit,
  prepareSettingsForSave,
  prepareSettingsPatch,
  settingsApi,
  type BackupItem,
  type BackupState,
  type BackupTestResult,
  type ImageStorageTestResult,
} from '@/api/settings'
import { parseProxyReference, proxyApi, type ClearanceTestResult, type ProxyRuntimeStatus, type ProxyTestResult } from '@/api/proxy'
import { userKeysApi, type UserKey } from '@/api/userKeys'
import { getAuthToken } from '@/api/client'
import { useConfirmDialog } from '@/composables/useConfirmDialog'
import { useSettingsStore } from '@/stores/settings'
import { useToast } from '@/composables/useToast'
import { ConsoleSegmentedTabs, ModalBody, ModalFooter, ModalHeader, ModalShell, PageLoadingState, PagePanel, StateBlock, SurfaceBox } from '@/components/ai'
import type { Settings } from '@/types/api'

type NumberFieldBinding = {
  input: ReturnType<typeof ref<string>>
  update: (value: string) => void
}

const settingsStore = useSettingsStore()
const { settings } = storeToRefs(settingsStore)
const toast = useToast()
const confirmDialog = useConfirmDialog()

const localSettings = ref<Settings | null>(null)
const savedSettingsBaseline = ref<Settings | null>(null)
const activeSettingsTab = ref('basic')
const isSaving = ref(false)
const settingsLoadError = ref('')
const imageStorageBusy = ref('')
const imageStorageTestResult = ref<ImageStorageTestResult | null>(null)
const proxyBusy = ref('')
const proxyTestResult = ref<ProxyTestResult | null>(null)
const proxyRuntimeLoading = ref(false)
const proxyRuntimeTesting = ref(false)
const proxyRuntimeStatus = ref<ProxyRuntimeStatus | null>(null)
const clearanceTestTarget = ref('https://chatgpt.com')
const clearanceTestResult = ref<ClearanceTestResult | null>(null)
const backupBusy = ref('')
const backupLoading = ref(false)
const backupState = ref<BackupState | null>(null)
const backupItems = ref<BackupItem[]>([])
const backupTestResult = ref<BackupTestResult | null>(null)
const cpaLoading = ref(false)
const sub2apiLoading = ref(false)
const savingExternalSource = ref('')
const testingExternalSource = ref('')
const externalSourceModal = ref<'cpa' | 'sub2api' | ''>('')
const cpaPools = ref<CPAPool[]>([])
const sub2apiServers = ref<Sub2APIServer[]>([])
const sub2apiGroups = ref<Record<string, Sub2APIRemoteGroup[]>>({})
const sub2apiGroupsLoadingId = ref('')
const editingCPAPoolId = ref('')
const editingSub2APIId = ref('')
const userKeys = ref<UserKey[]>([])
const userKeysLoading = ref(false)
const userKeyBusy = ref('')
const userKeyModal = ref<'create' | 'edit' | ''>('')
const editingUserKey = ref<UserKey | null>(null)
const newUserKey = ref('')
const cpaForm = ref({
  name: '',
  base_url: '',
  secret_key: '',
})
const sub2apiForm = ref({
  name: '',
  base_url: '',
  email: '',
  password: '',
  api_key: '',
  group_id: '',
})
const userKeyForm = ref({
  name: '',
  key: '',
})
let hasActivatedOnce = false

const externalSourcesLoading = computed(() => cpaLoading.value || sub2apiLoading.value)

const registerPostprocessGroupIdsText = computed<string>({
  get: () => (localSettings.value?.register_postprocess?.group_ids || []).join(', '),
  set: (val: string) => {
    if (!localSettings.value) return
    const ids = String(val)
      .split(',')
      .map((item) => Number(item.trim()))
      .filter((item) => Number.isInteger(item) && item > 0)
    localSettings.value.register_postprocess.group_ids = ids
  },
})

const settingsTabs = [
  { value: 'basic', label: '基础配置' },
  { value: 'image-errors', label: '图片错误' },
  { value: 'storage', label: '图片存储与审核' },
  { value: 'backup', label: 'R2 备份' },
  { value: 'keys', label: '用户密钥' },
  { value: 'api-docs', label: '接口接入' },
  { value: 'canvas', label: '画布入口' },
  { value: 'register-postprocess', label: '注册入库' },
  { value: 'cpa', label: 'CPA' },
  { value: 'sub2api', label: 'Sub2API' },
]

type ImageErrorMessageKey = keyof Settings['image_error_messages']

const imageErrorMessageFields: Array<{
  key: ImageErrorMessageKey
  label: string
  placeholder: string
  help?: string
}> = [
  {
    key: 'fallback',
    label: '兜底错误',
    placeholder: '图片生成请求失败，请稍后重试。',
  },
  {
    key: 'quota',
    label: '额度耗尽',
    placeholder: '图片账号额度已用完，请稍后再试或联系管理员。',
  },
  {
    key: 'no_account',
    label: '账号暂不可用',
    placeholder: '当前图片账号暂不可用，可能是账号池、并发或上游波动，请稍后重试。',
  },
  {
    key: 'local_busy',
    label: '本地繁忙 / 无可用账号',
    placeholder: '当前没有可用的图片账号或账号并发已满，请稍后重试。',
  },
  {
    key: 'unsupported_model',
    label: '模型不支持',
    placeholder: '当前模型不支持图片生成，请检查 model 参数。',
  },
  {
    key: 'poll_timeout',
    label: '轮询超时',
    placeholder: '图片任务暂未返回结果，可能仍在排队或上游处理较慢，请重试。',
  },
  {
    key: 'stream_interrupted',
    label: '上游断流',
    placeholder: '图片生成连接中断，可能是上游服务繁忙或网络波动，请重试。',
  },
  {
    key: 'connection_failed',
    label: '连接失败',
    placeholder: '连接上游图片服务失败，可能是网络或代理波动，请重试。',
  },
  {
    key: 'connection_timeout',
    label: '连接超时',
    placeholder: '连接上游图片服务超时，请稍后重试。',
  },
  {
    key: 'token_invalid',
    label: '账号状态异常',
    placeholder: '图片生成账号状态异常，请稍后重试。',
  },
  {
    key: 'text_reply',
    label: '返回文本但无图',
    placeholder: '上游返回了文本说明，未生成图片。请调整提示词或重试。',
    help: '可使用 {text} 指定上游文本插入位置；不写占位符时会自动追加到下一行。',
  },
]

const logLevelOptions = ['debug', 'info', 'warning', 'error']
const backupIncludeOptions = [
  { value: 'config', label: '系统配置' },
  { value: 'register', label: '注册配置' },
  { value: 'cpa', label: 'CPA 配置' },
  { value: 'sub2api', label: 'Sub2API 配置' },
  { value: 'logs', label: '调度与调用日志' },
  { value: 'dashboard_metrics', label: '概览统计' },
  { value: 'image_tasks', label: '图片任务记录' },
  { value: 'accounts_snapshot', label: '账号快照' },
  { value: 'auth_keys_snapshot', label: '用户密钥快照' },
  { value: 'images', label: '图片文件目录' },
] as const

const serviceBaseUrl = computed(() => window.location.origin)
const openAIBaseUrl = computed(() => `${serviceBaseUrl.value.replace(/\/$/, '')}/v1`)
const currentApiKey = computed(() => getAuthToken() || '<当前密钥>')
const apiDocItems = computed(() => [
  {
    title: '模型列表',
    method: 'GET',
    path: '/v1/models',
    description: '返回 OpenAI 兼容模型列表。',
    example: `curl ${openAIBaseUrl.value}/models \\\n  -H "Authorization: Bearer ${currentApiKey.value}"`,
  },
  {
    title: '聊天补全',
    method: 'POST',
    path: '/v1/chat/completions',
    description: 'OpenAI 兼容聊天补全接口，图片兼容场景也会解析 n 等参数。',
    example: `curl ${openAIBaseUrl.value}/chat/completions \\\n  -H "Content-Type: application/json" \\\n  -H "Authorization: Bearer ${currentApiKey.value}" \\\n  -d '{"model":"gpt-5-mini","messages":[{"role":"user","content":"你好"}]}'`,
  },
  {
    title: 'Responses',
    method: 'POST',
    path: '/v1/responses',
    description: '兼容 Responses 输入结构，支持文本与工具调用场景。',
    example: `curl ${openAIBaseUrl.value}/responses \\\n  -H "Content-Type: application/json" \\\n  -H "Authorization: Bearer ${currentApiKey.value}" \\\n  -d '{"model":"gpt-5-mini","input":"生成一张未来城市图片"}'`,
  },
  {
    title: 'Messages',
    method: 'POST',
    path: '/v1/messages',
    description: 'Anthropic Messages 兼容入口，支持 Authorization Bearer 或 x-api-key 鉴权。',
    example: `curl ${openAIBaseUrl.value}/messages \\\n  -H "Content-Type: application/json" \\\n  -H "Authorization: Bearer ${currentApiKey.value}" \\\n  -d '{"model":"gpt-5-mini","max_tokens":1024,"messages":[{"role":"user","content":"你好"}]}'`,
  },
  {
    title: '联网搜索',
    method: 'POST',
    path: '/v1/search',
    description: '本地搜索兼容入口，返回 answer 与 sources。',
    example: `curl ${openAIBaseUrl.value}/search \\\n  -H "Content-Type: application/json" \\\n  -H "Authorization: Bearer ${currentApiKey.value}" \\\n  -d '{"prompt":"今天的 OpenAI 新闻"}'`,
  },
  {
    title: '图片生成',
    method: 'POST',
    path: '/v1/images/generations',
    description: '图片生成接口，支持 prompt、model、n、size、quality 等参数。',
    example: `curl ${openAIBaseUrl.value}/images/generations \\\n  -H "Content-Type: application/json" \\\n  -H "Authorization: Bearer ${currentApiKey.value}" \\\n  -d '{"model":"gpt-image-2","prompt":"一张极简产品海报","n":1}'`,
  },
  {
    title: '图片编辑',
    method: 'POST',
    path: '/v1/images/edits',
    description: '图片编辑接口，支持 multipart 上传参考图。',
    example: `curl ${openAIBaseUrl.value}/images/edits \\\n  -H "Authorization: Bearer ${currentApiKey.value}" \\\n  -F "model=gpt-image-2" \\\n  -F "prompt=改成赛博朋克夜景" \\\n  -F "image=@./input.png"`,
  },
  {
    title: '创建可编辑文件任务',
    method: 'POST',
    path: '/v1/editable-file-tasks',
    description: '统一创建 PPT/PSD 文件任务，kind 可填 ppt 或 psd。',
    example: `curl ${openAIBaseUrl.value}/editable-file-tasks \\\n  -H "Content-Type: application/json" \\\n  -H "Authorization: Bearer ${currentApiKey.value}" \\\n  -d '{"kind":"ppt","prompt":"做一份产品发布会 PPT"}'`,
  },
  {
    title: '查询可编辑文件任务',
    method: 'GET',
    path: '/v1/editable-file-tasks?ids={taskId1,taskId2}',
    description: '按任务 ID 查询 PPT/PSD 文件生成状态。',
    example: `curl "${openAIBaseUrl.value}/editable-file-tasks?ids=task_1,task_2" \\\n  -H "Authorization: Bearer ${currentApiKey.value}"`,
  },
  {
    title: 'PPT 生成任务',
    method: 'POST',
    path: '/v1/ppt/generations',
    description: '直接创建 PPT 生成任务，返回任务 ID 后再查询状态。',
    example: `curl ${openAIBaseUrl.value}/ppt/generations \\\n  -H "Content-Type: application/json" \\\n  -H "Authorization: Bearer ${currentApiKey.value}" \\\n  -d '{"prompt":"生成一份市场分析 PPT"}'`,
  },
  {
    title: 'PSD 生成任务',
    method: 'POST',
    path: '/v1/psd/generations',
    description: '直接创建 PSD 生成任务，返回任务 ID 后再查询状态。',
    example: `curl ${openAIBaseUrl.value}/psd/generations \\\n  -H "Content-Type: application/json" \\\n  -H "Authorization: Bearer ${currentApiKey.value}" \\\n  -d '{"prompt":"生成一张电商海报 PSD"}'`,
  },
  {
    title: '文件下载',
    method: 'GET',
    path: '/files/{file_path}',
    description: '下载 PPT/PSD 任务生成的公开文件。',
    example: `curl ${serviceBaseUrl.value}/files/{file_path}`,
  },
])

const backupStatusText = computed(() => {
  const state = backupState.value
  if (!state) return '未加载'
  if (state.running) return '备份中'
  if (state.last_status === 'success') return '最近成功'
  if (state.last_status === 'error') return '最近失败'
  return state.last_status || '未执行'
})

const imageStorageModeOptions = [
  { label: '仅本地', value: 'local' },
  { label: '仅 WebDAV', value: 'webdav' },
  { label: '本地 + WebDAV', value: 'both' },
]

const proxyRuntimeEgressOptions = [
  { label: '直连', value: 'direct' },
  { label: '单代理', value: 'single_proxy' },
]

const proxyClearanceModeOptions = [
  { label: '关闭', value: 'none' },
  { label: 'FlareSolverr', value: 'flaresolverr' },
  { label: '手动 Cookie', value: 'manual' },
]

const proxyRuntimeSummaryItems = computed(() => {
  const status = proxyRuntimeStatus.value
  return [
    { label: '运行时', value: status ? (status.enabled ? '已启用' : '关闭') : '-' },
    { label: '出站方式', value: status ? (status.egress_mode === 'single_proxy' ? '单代理' : '直连') : '-' },
    { label: '代理', value: status ? (status.has_proxy ? '已配置' : '未配置') : '-' },
    { label: '清障', value: status ? (status.clearance_enabled ? `已启用 / ${status.clearance_mode}` : '关闭') : '-' },
    { label: '缓存', value: status ? (status.has_clearance_bundle ? '已有 clearance' : '暂无缓存') : '-' },
  ]
})

const sensitiveWordsText = computed({
  get: () => (localSettings.value?.sensitive_words || []).join('\n'),
  set: (value: string) => {
    if (!localSettings.value) return
    localSettings.value.sensitive_words = value
      .split(/\r?\n/)
      .map((item) => item.trim())
      .filter(Boolean)
  },
})

const numberValue = (value: unknown, fallback: number, min: number, max?: number): number => {
  const parsed = Number(value)
  const finite = Number.isFinite(parsed) ? parsed : fallback
  const bounded = Math.max(min, finite)
  return typeof max === 'number' ? Math.min(max, bounded) : bounded
}

const intValue = (value: unknown, fallback: number, min: number, max?: number): number => (
  Math.round(numberValue(value, fallback, min, max))
)

const createNumberField = (
  getter: () => number,
  setter: (value: number) => void,
  options: { integer?: boolean; min?: number; max?: number; fallback?: number } = {},
): NumberFieldBinding => {
  const input = ref('')

  watch(getter, (value) => {
    const next = String(value)
    if (input.value !== next) {
      input.value = next
    }
  }, { immediate: true })

  const update = (value: string) => {
    input.value = value
    const parsed = Number(value)
    if (value.trim() === '' || !Number.isFinite(parsed)) return
    const min = options.min ?? 0
    const fallback = options.fallback ?? getter()
    const next = options.integer
      ? intValue(parsed, fallback, min, options.max)
      : numberValue(parsed, fallback, min, options.max)
    setter(next)
  }

  return { input, update }
}

const settingsFingerprint = (value: Settings | null | undefined): string => (
  value ? JSON.stringify(prepareSettingsForSave(value)) : ''
)

const hasUnsavedSettings = computed(() => {
  if (!localSettings.value || !savedSettingsBaseline.value) return false
  return settingsFingerprint(localSettings.value) !== settingsFingerprint(savedSettingsBaseline.value)
})

function requireSavedSettings(actionLabel: string) {
  if (!localSettings.value) return false
  if (hasUnsavedSettings.value) {
    toast.warning(`请先保存设置，再${actionLabel}`)
    return false
  }
  return true
}

const imageRetentionDaysField = createNumberField(
  () => localSettings.value?.image_retention_days ?? 15,
  (value) => {
    if (!localSettings.value) return
    localSettings.value.image_retention_days = value
  },
  { integer: true, min: 1, fallback: 15 },
)
const logRetentionDaysField = createNumberField(
  () => localSettings.value?.log_retention_days ?? 30,
  (value) => {
    if (!localSettings.value) return
    localSettings.value.log_retention_days = value
  },
  { integer: true, min: 1, fallback: 30 },
)
const refreshAccountIntervalField = createNumberField(
  () => localSettings.value?.refresh_account_interval_minute ?? 5,
  (value) => {
    if (!localSettings.value) return
    localSettings.value.refresh_account_interval_minute = value
  },
  { integer: true, min: 1, fallback: 5 },
)
const imagePollTimeoutField = createNumberField(
  () => localSettings.value?.image_poll_timeout_secs ?? 120,
  (value) => {
    if (!localSettings.value) return
    localSettings.value.image_poll_timeout_secs = value
  },
  { integer: true, min: 1, fallback: 120 },
)
const imageStreamTimeoutField = createNumberField(
  () => localSettings.value?.image_stream_timeout_secs ?? 300,
  (value) => {
    if (!localSettings.value) return
    localSettings.value.image_stream_timeout_secs = value
  },
  { integer: true, min: 1, fallback: 300 },
)
const imageAccountConcurrencyField = createNumberField(
  () => localSettings.value?.image_account_concurrency ?? 3,
  (value) => {
    if (!localSettings.value) return
    localSettings.value.image_account_concurrency = value
  },
  { integer: true, min: 1, fallback: 3 },
)
const imageTimeoutRetryField = createNumberField(
  () => localSettings.value?.image_timeout_retry_secs ?? 30,
  (value) => {
    if (!localSettings.value) return
    localSettings.value.image_timeout_retry_secs = value
  },
  { integer: true, min: 1, fallback: 30 },
)
const imageSettleSecondsField = createNumberField(
  () => localSettings.value?.image_settle_secs ?? 5,
  (value) => {
    if (!localSettings.value) return
    localSettings.value.image_settle_secs = value
  },
  { min: 0.5, fallback: 5 },
)
const clearanceTimeoutField = createNumberField(
  () => localSettings.value?.proxy_runtime?.clearance.timeout_sec ?? 60,
  (value) => {
    if (!localSettings.value) return
    localSettings.value.proxy_runtime = normalizeProxyRuntime(localSettings.value.proxy_runtime)
    localSettings.value.proxy_runtime.clearance.timeout_sec = value
  },
  { integer: true, min: 1, fallback: 60 },
)
const clearanceRefreshIntervalField = createNumberField(
  () => localSettings.value?.proxy_runtime?.clearance.refresh_interval ?? 3600,
  (value) => {
    if (!localSettings.value) return
    localSettings.value.proxy_runtime = normalizeProxyRuntime(localSettings.value.proxy_runtime)
    localSettings.value.proxy_runtime.clearance.refresh_interval = value
  },
  { integer: true, min: 60, fallback: 3600 },
)
const backupIntervalMinutesField = createNumberField(
  () => localSettings.value?.backup?.interval_minutes ?? 1440,
  (value) => { if (localSettings.value) localSettings.value.backup.interval_minutes = value },
  { integer: true, min: 1, fallback: 1440 },
)
const backupRotationKeepField = createNumberField(
  () => localSettings.value?.backup?.rotation_keep ?? 10,
  (value) => { if (localSettings.value) localSettings.value.backup.rotation_keep = value },
  { integer: true, min: 0, fallback: 10 },
)

function formatBytes(value: unknown) {
  const bytes = Number(value) || 0
  if (bytes <= 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let size = bytes
  let unitIndex = 0
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024
    unitIndex += 1
  }
  return `${size.toFixed(unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`
}

function formatDateTime(value: unknown) {
  const raw = String(value || '').trim()
  if (!raw) return '-'
  const parsed = new Date(raw)
  if (Number.isNaN(parsed.getTime())) return raw
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(parsed)
}

async function copyUserKey(value: string) {
  if (!value) return
  try {
    await navigator.clipboard.writeText(value)
    toast.success('已复制密钥')
  } catch {
    toast.error('复制失败，请手动复制')
  }
}

function setLogLevel(level: string, enabled: boolean) {
  if (!localSettings.value) return
  const current = Array.isArray(localSettings.value.log_levels)
    ? localSettings.value.log_levels
    : []
  localSettings.value.log_levels = enabled
    ? Array.from(new Set([...current, level]))
    : current.filter((item) => item !== level)
}

async function testDefaultProxy() {
  const candidate = String(localSettings.value?.proxy || '').trim()
  const reference = parseProxyReference(candidate)
  if (reference.mode === 'global' || reference.mode === 'direct') {
    toast.info('直连模式无需测试出口')
    return
  }
  if (reference.mode === 'group' && !reference.value) {
    toast.warning('请填写代理组 ID')
    return
  }
  if ((reference.mode === 'custom' || reference.mode === 'profile') && !reference.value) {
    toast.warning('请先填写默认出口')
    return
  }
  const confirmed = await confirmDialog.ask({
    title: '测试默认出口',
    message: '即将使用当前填写的默认出口发起连接测试，不会保存设置。是否继续？',
    confirmText: '开始测试',
    cancelText: '取消',
  })
  if (!confirmed) return

  proxyBusy.value = 'test'
  proxyTestResult.value = null
  try {
    if (reference.mode === 'group') {
      const response = await proxyApi.testGroup({ id: reference.value })
      const results = response.results || []
      const failed = results.filter((item) => !item.result.ok)
      const firstResult = results[0]?.result
      proxyTestResult.value = {
        ok: results.length > 0 && failed.length === 0,
        status: firstResult?.status || 0,
        latency_ms: results.reduce((max, item) => Math.max(max, Number(item.result.latency_ms || 0)), 0),
        error: failed.length ? `代理组检测完成，失败 ${failed.length} 个节点` : null,
      }
      if (proxyTestResult.value.ok) {
        toast.success(`默认出口代理组可用：${results.length} 个节点`)
      } else {
        toast.warning(proxyTestResult.value.error || '代理组测试失败')
      }
      return
    }
    if (reference.mode === 'profile') {
      const response = await proxyApi.testProfile({ id: reference.value })
      proxyTestResult.value = response.result
      if (response.result.ok) {
        toast.success(`出口可用：${response.result.latency_ms} ms`)
      } else {
        toast.warning(response.result.error || '出口测试失败')
      }
      return
    }
    const response = await proxyApi.test(candidate)
    proxyTestResult.value = response.result
    if (response.result.ok) {
      toast.success(`出口可用：${response.result.latency_ms} ms`)
    } else {
      toast.warning(response.result.error || '出口测试失败')
    }
  } catch (error: any) {
    proxyTestResult.value = {
      ok: false,
      status: 0,
      latency_ms: 0,
      error: error.message || '出口测试失败',
    }
    toast.error(error.message || '出口测试失败')
  } finally {
    proxyBusy.value = ''
  }
}

async function loadProxyRuntimeStatus(silent = false) {
  proxyRuntimeLoading.value = true
  try {
    const response = await proxyApi.getRuntime()
    proxyRuntimeStatus.value = response.status
    if (localSettings.value && !localSettings.value.proxy_runtime) {
      localSettings.value.proxy_runtime = normalizeProxyRuntime(response.runtime)
    }
  } catch (error: any) {
    proxyRuntimeStatus.value = null
    if (!silent) toast.error(error.message || '加载稳定代理状态失败')
  } finally {
    proxyRuntimeLoading.value = false
  }
}

async function testProxyClearance() {
  if (!requireSavedSettings('测试 Cloudflare 清障')) return
  proxyRuntimeTesting.value = true
  clearanceTestResult.value = null
  try {
    const response = await proxyApi.testClearance(clearanceTestTarget.value)
    clearanceTestResult.value = response.result
    if (response.result.runtime) proxyRuntimeStatus.value = response.result.runtime
    if (response.result.ok) {
      toast.success(`Cloudflare 清障可用：${response.result.latency_ms} ms`)
    } else {
      toast.warning(response.result.error || 'Cloudflare 清障测试失败')
    }
  } catch (error: any) {
    clearanceTestResult.value = {
      ok: false,
      status: 'error',
      latency_ms: 0,
      has_cookies: false,
      user_agent: '',
      error: error.message || 'Cloudflare 清障测试失败',
    }
    toast.error(error.message || 'Cloudflare 清障测试失败')
  } finally {
    proxyRuntimeTesting.value = false
  }
}

function resetUserKeyForm() {
  userKeyForm.value = { name: '', key: '' }
  editingUserKey.value = null
}

function openUserKeyCreateModal() {
  resetUserKeyForm()
  userKeyModal.value = 'create'
}

function openUserKeyEditModal(item: UserKey) {
  editingUserKey.value = item
  userKeyForm.value = {
    name: item.name || '',
    key: '',
  }
  userKeyModal.value = 'edit'
}

function closeUserKeyModal() {
  if (userKeyBusy.value === 'create') return
  if (editingUserKey.value && userKeyBusy.value === editingUserKey.value.id) return
  userKeyModal.value = ''
  resetUserKeyForm()
}

async function loadUserKeys() {
  userKeysLoading.value = true
  try {
    const response = await userKeysApi.list()
    userKeys.value = Array.isArray(response.items) ? response.items : []
  } catch (error: any) {
    userKeys.value = []
    toast.error(error.message || '加载用户密钥失败')
  } finally {
    userKeysLoading.value = false
  }
}

async function createUserKey() {
  userKeyBusy.value = 'create'
  try {
    const response = await userKeysApi.create(userKeyForm.value.name.trim())
    userKeys.value = response.items || []
    newUserKey.value = response.key || ''
    toast.success('用户密钥已创建')
    userKeyModal.value = ''
    resetUserKeyForm()
  } catch (error: any) {
    toast.error(error.message || '创建用户密钥失败')
  } finally {
    userKeyBusy.value = ''
  }
}

async function updateUserKey() {
  const item = editingUserKey.value
  if (!item) return
  const nextName = userKeyForm.value.name.trim()
  const nextKey = userKeyForm.value.key.trim()
  const updates: { name?: string; key?: string } = {}
  if (nextName !== item.name) updates.name = nextName
  if (nextKey) updates.key = nextKey
  if (!Object.keys(updates).length) {
    closeUserKeyModal()
    return
  }

  userKeyBusy.value = item.id
  try {
    const response = await userKeysApi.update(item.id, updates)
    userKeys.value = response.items || []
    toast.success(nextKey ? '用户密钥已更新' : '用户名称已更新')
    userKeyModal.value = ''
    resetUserKeyForm()
  } catch (error: any) {
    toast.error(error.message || '更新用户密钥失败')
  } finally {
    userKeyBusy.value = ''
  }
}

async function toggleUserKey(item: UserKey) {
  userKeyBusy.value = item.id
  try {
    const response = await userKeysApi.update(item.id, { enabled: !item.enabled })
    userKeys.value = response.items || []
    toast.success(item.enabled ? '用户密钥已禁用' : '用户密钥已启用')
  } catch (error: any) {
    toast.error(error.message || '更新用户密钥失败')
  } finally {
    userKeyBusy.value = ''
  }
}

async function deleteUserKey(item: UserKey) {
  const confirmed = await confirmDialog.ask({
    title: '删除用户密钥',
    message: `确定删除用户密钥「${item.name || item.id}」吗？删除后这条密钥将无法继续调用接口。`,
    confirmText: '删除',
    cancelText: '取消',
  })
  if (!confirmed) return

  userKeyBusy.value = item.id
  try {
    const response = await userKeysApi.delete(item.id)
    userKeys.value = response.items || []
    if (editingUserKey.value?.id === item.id) {
      userKeyModal.value = ''
      resetUserKeyForm()
    }
    toast.success('用户密钥已删除')
  } catch (error: any) {
    toast.error(error.message || '删除用户密钥失败')
  } finally {
    userKeyBusy.value = ''
  }
}

async function persistSettings(showToast = false) {
  if (!localSettings.value) return null
  const payload = prepareSettingsPatch(localSettings.value, savedSettingsBaseline.value)
  const result = await settingsStore.updateSettingsPatch(payload)
  if (result.config) {
    const next = prepareSettingsForEdit(result.config)
    localSettings.value = next
    savedSettingsBaseline.value = prepareSettingsForEdit(next)
  }
  await loadProxyRuntimeStatus(true)
  if (showToast) toast.success('设置保存成功')
  return result
}

async function testImageStorageConnection() {
  if (!requireSavedSettings('测试 WebDAV')) return
  const confirmed = await confirmDialog.ask({
    title: '确认测试 WebDAV',
    message: '即将使用已保存的图片存储配置发起 WebDAV 连接测试，可能访问外部存储服务。是否继续？',
    confirmText: '开始测试',
    cancelText: '取消',
  })
  if (!confirmed) return

  imageStorageBusy.value = 'test'
  imageStorageTestResult.value = null
  try {
    const response = await settingsApi.testImageStorage()
    imageStorageTestResult.value = response.result
    if (response.result.ok) toast.success('WebDAV 测试通过')
    else toast.warning(response.result.error || 'WebDAV 测试失败')
  } catch (error: any) {
    imageStorageTestResult.value = { ok: false, error: error.message || 'WebDAV 测试失败' }
    toast.error(error.message || 'WebDAV 测试失败')
  } finally {
    imageStorageBusy.value = ''
  }
}

async function syncImageStorageFiles() {
  if (!requireSavedSettings('同步本地图片')) return
  const confirmed = await confirmDialog.ask({
    title: '确认同步图片存储',
    message: '即将扫描本地图片并同步到已配置的 WebDAV 存储，可能产生外部上传流量。是否继续？',
    confirmText: '开始同步',
    cancelText: '取消',
  })
  if (!confirmed) return

  imageStorageBusy.value = 'sync'
  try {
    const response = await settingsApi.syncImageStorage()
    toast.success(`同步完成：上传 ${response.result.uploaded}，跳过 ${response.result.skipped}，失败 ${response.result.failed}`)
  } catch (error: any) {
    toast.error(error.message || '同步图片失败')
  } finally {
    imageStorageBusy.value = ''
  }
}

async function loadBackups() {
  backupLoading.value = true
  try {
    const response = await settingsApi.listBackups()
    backupItems.value = Array.isArray(response.items) ? response.items : []
    backupState.value = response.state || null
  } catch (error: any) {
    backupItems.value = []
    backupState.value = null
    toast.error(error.message || '加载备份历史失败')
  } finally {
    backupLoading.value = false
  }
}

async function testBackupConnection() {
  if (!requireSavedSettings('测试备份连接')) return
  const confirmed = await confirmDialog.ask({
    title: '确认测试备份连接',
    message: '即将使用已保存的备份配置发起 R2/备份存储连接测试，可能访问外部存储服务。是否继续？',
    confirmText: '开始测试',
    cancelText: '取消',
  })
  if (!confirmed) return

  backupBusy.value = 'test'
  backupTestResult.value = null
  try {
    const response = await settingsApi.testBackup()
    backupTestResult.value = response.result
    if (response.result.ok) toast.success('备份连接测试通过')
    else toast.warning(response.result.error || '备份连接测试失败')
  } catch (error: any) {
    backupTestResult.value = { ok: false, error: error.message || '备份连接测试失败' }
    toast.error(error.message || '备份连接测试失败')
  } finally {
    backupBusy.value = ''
  }
}

async function runBackupNow() {
  if (!requireSavedSettings('执行立即备份')) return
  const confirmed = await confirmDialog.ask({
    title: '确认立即备份',
    message: '即将把当前配置和运行数据写入备份存储，可能产生外部上传流量。是否继续？',
    confirmText: '开始备份',
    cancelText: '取消',
  })
  if (!confirmed) return

  backupBusy.value = 'run'
  try {
    const response = await settingsApi.runBackup()
    toast.success(`备份已完成：${response.result.key}`)
    await loadBackups()
  } catch (error: any) {
    toast.error(error.message || '执行备份失败')
  } finally {
    backupBusy.value = ''
  }
}

async function deleteBackupItem(item: BackupItem) {
  const confirmed = await confirmDialog.ask({
    title: '删除备份',
    message: `确定删除备份 ${item.name || item.key}？`,
    confirmText: '删除',
    cancelText: '取消',
  })
  if (!confirmed) return

  backupBusy.value = item.key
  try {
    await settingsApi.deleteBackup(item.key)
    toast.success('备份已删除')
    await loadBackups()
  } catch (error: any) {
    toast.error(error.message || '删除备份失败')
  } finally {
    backupBusy.value = ''
  }
}

function resetCPAForm() {
  editingCPAPoolId.value = ''
  cpaForm.value = {
    name: '',
    base_url: '',
    secret_key: '',
  }
}

function openCPAModal(pool?: CPAPool) {
  if (pool) {
    editCPAPool(pool)
    return
  }
  resetCPAForm()
  externalSourceModal.value = 'cpa'
}

function editCPAPool(pool: CPAPool) {
  editingCPAPoolId.value = pool.id
  cpaForm.value = {
    name: pool.name || '',
    base_url: pool.base_url || '',
    secret_key: '',
  }
  externalSourceModal.value = 'cpa'
}

async function loadCPAPools() {
  cpaLoading.value = true
  try {
    const response = await accountImportsApi.listCPAPools()
    cpaPools.value = Array.isArray(response.pools) ? response.pools : []
  } catch (error: any) {
    cpaPools.value = []
    toast.error(error.message || '加载 CPA 连接失败')
  } finally {
    cpaLoading.value = false
  }
}

async function saveCPAPool() {
  const payload = {
    name: cpaForm.value.name.trim(),
    base_url: cpaForm.value.base_url.trim(),
    secret_key: cpaForm.value.secret_key.trim(),
  }
  if (!payload.base_url) {
    toast.warning('请输入 CPA 地址')
    return
  }
  if (!editingCPAPoolId.value && !payload.secret_key) {
    toast.warning('新增 CPA 连接需要管理密钥')
    return
  }

  savingExternalSource.value = 'cpa'
  try {
    const response = editingCPAPoolId.value
      ? await accountImportsApi.updateCPAPool(editingCPAPoolId.value, {
          name: payload.name,
          base_url: payload.base_url,
          ...(payload.secret_key ? { secret_key: payload.secret_key } : {}),
        })
      : await accountImportsApi.createCPAPool(payload)
    cpaPools.value = response.pools || []
    resetCPAForm()
    externalSourceModal.value = ''
    toast.success('CPA 连接已保存')
  } catch (error: any) {
    toast.error(error.message || '保存 CPA 连接失败')
  } finally {
    savingExternalSource.value = ''
  }
}

async function deleteCPAPool(pool: CPAPool) {
  const confirmed = await confirmDialog.ask({
    title: '删除 CPA 连接',
    message: `确定删除 ${pool.name || pool.base_url}？账号页将不能再从这个 CPA 连接导入。`,
    confirmText: '删除',
    cancelText: '取消',
  })
  if (!confirmed) return

  savingExternalSource.value = pool.id
  try {
    const response = await accountImportsApi.deleteCPAPool(pool.id)
    cpaPools.value = response.pools || []
    if (editingCPAPoolId.value === pool.id) resetCPAForm()
    toast.success('CPA 连接已删除')
  } catch (error: any) {
    toast.error(error.message || '删除 CPA 连接失败')
  } finally {
    savingExternalSource.value = ''
  }
}

async function testCPAPool(pool: CPAPool) {
  const confirmed = await confirmDialog.ask({
    title: '测试 CPA 连接',
    message: `即将访问 CPA 连接 ${pool.name || pool.base_url || pool.id} 并读取远程文件列表。请确认当前允许连接该外部服务。`,
    confirmText: '开始测试',
    cancelText: '取消',
  })
  if (!confirmed) return

  testingExternalSource.value = pool.id
  try {
    const response = await accountImportsApi.listCPAPoolFiles(pool.id)
    toast.success(`CPA 连接可用，读取到 ${response.files?.length || 0} 个文件`)
  } catch (error: any) {
    toast.error(error.message || 'CPA 连接测试失败')
  } finally {
    testingExternalSource.value = ''
  }
}

function resetSub2APIForm() {
  editingSub2APIId.value = ''
  sub2apiForm.value = {
    name: '',
    base_url: '',
    email: '',
    password: '',
    api_key: '',
    group_id: '',
  }
}

function openSub2APIModal(server?: Sub2APIServer) {
  if (server) {
    editSub2APIServer(server)
    return
  }
  resetSub2APIForm()
  externalSourceModal.value = 'sub2api'
}

function editSub2APIServer(server: Sub2APIServer) {
  editingSub2APIId.value = server.id
  sub2apiForm.value = {
    name: server.name || '',
    base_url: server.base_url || '',
    email: server.email || '',
    password: '',
    api_key: '',
    group_id: server.group_id || '',
  }
  externalSourceModal.value = 'sub2api'
}

async function loadSub2APIServers() {
  sub2apiLoading.value = true
  try {
    const response = await accountImportsApi.listSub2APIServers()
    sub2apiServers.value = Array.isArray(response.servers) ? response.servers : []
  } catch (error: any) {
    sub2apiServers.value = []
    toast.error(error.message || '加载 Sub2API 连接失败')
  } finally {
    sub2apiLoading.value = false
  }
}

async function saveSub2APIServer() {
  const payload = {
    name: sub2apiForm.value.name.trim(),
    base_url: sub2apiForm.value.base_url.trim(),
    email: sub2apiForm.value.email.trim(),
    password: sub2apiForm.value.password,
    api_key: sub2apiForm.value.api_key.trim(),
    group_id: sub2apiForm.value.group_id.trim(),
  }
  if (!payload.base_url) {
    toast.warning('请输入 Sub2API 地址')
    return
  }
  const hasLogin = Boolean(payload.email && payload.password)
  const hasApiKey = Boolean(payload.api_key)
  if (!editingSub2APIId.value && !hasLogin && !hasApiKey) {
    toast.warning('新增 Sub2API 连接需要邮箱密码或 Admin API Key')
    return
  }

  savingExternalSource.value = 'sub2api'
  try {
    const response = editingSub2APIId.value
      ? await accountImportsApi.updateSub2APIServer(editingSub2APIId.value, {
          name: payload.name,
          base_url: payload.base_url,
          email: payload.email,
          group_id: payload.group_id,
          ...(payload.password ? { password: payload.password } : {}),
          ...(payload.api_key ? { api_key: payload.api_key } : {}),
        })
      : await accountImportsApi.createSub2APIServer(payload)
    sub2apiServers.value = response.servers || []
    resetSub2APIForm()
    externalSourceModal.value = ''
    toast.success('Sub2API 连接已保存')
  } catch (error: any) {
    toast.error(error.message || '保存 Sub2API 连接失败')
  } finally {
    savingExternalSource.value = ''
  }
}

async function deleteSub2APIServer(server: Sub2APIServer) {
  const confirmed = await confirmDialog.ask({
    title: '删除 Sub2API 连接',
    message: `确定删除 ${server.name || server.base_url}？账号页将不能再从这个 Sub2API 连接导入。`,
    confirmText: '删除',
    cancelText: '取消',
  })
  if (!confirmed) return

  savingExternalSource.value = server.id
  try {
    const response = await accountImportsApi.deleteSub2APIServer(server.id)
    sub2apiServers.value = response.servers || []
    const nextGroups = { ...sub2apiGroups.value }
    delete nextGroups[server.id]
    sub2apiGroups.value = nextGroups
    if (editingSub2APIId.value === server.id) resetSub2APIForm()
    toast.success('Sub2API 连接已删除')
  } catch (error: any) {
    toast.error(error.message || '删除 Sub2API 连接失败')
  } finally {
    savingExternalSource.value = ''
  }
}

async function loadSub2APIGroups(server: Sub2APIServer) {
  const confirmed = await confirmDialog.ask({
    title: '加载 Sub2API 分组',
    message: `即将访问 Sub2API 连接 ${server.name || server.base_url || server.id} 并读取远程分组列表。请确认当前允许连接该外部服务。`,
    confirmText: '确认加载',
    cancelText: '取消',
  })
  if (!confirmed) return

  sub2apiGroupsLoadingId.value = server.id
  try {
    const response = await accountImportsApi.listSub2APIServerGroups(server.id)
    sub2apiGroups.value = {
      ...sub2apiGroups.value,
      [server.id]: Array.isArray(response.groups) ? response.groups : [],
    }
    if (!response.groups?.length) toast.info('这个 Sub2API 连接没有返回分组')
  } catch (error: any) {
    toast.error(error.message || '读取 Sub2API 分组失败')
  } finally {
    sub2apiGroupsLoadingId.value = ''
  }
}

async function testSub2APIServer(server: Sub2APIServer) {
  const confirmed = await confirmDialog.ask({
    title: '测试 Sub2API 连接',
    message: `即将访问 Sub2API 连接 ${server.name || server.base_url || server.id} 并读取远程分组列表。请确认当前允许连接该外部服务。`,
    confirmText: '开始测试',
    cancelText: '取消',
  })
  if (!confirmed) return

  testingExternalSource.value = server.id
  try {
    const response = await accountImportsApi.listSub2APIServerGroups(server.id)
    sub2apiGroups.value = {
      ...sub2apiGroups.value,
      [server.id]: response.groups || [],
    }
    toast.success(`Sub2API 连接可用，读取到 ${response.groups?.length || 0} 个分组`)
  } catch (error: any) {
    toast.error(error.message || 'Sub2API 连接测试失败')
  } finally {
    testingExternalSource.value = ''
  }
}

function useSub2APIGroup(server: Sub2APIServer, groupId: string) {
  editSub2APIServer(server)
  sub2apiForm.value.group_id = groupId
  toast.info('已填入分组 ID，保存后生效')
}

function closeExternalSourceModal() {
  if (savingExternalSource.value === 'cpa' || savingExternalSource.value === 'sub2api') return
  externalSourceModal.value = ''
  resetCPAForm()
  resetSub2APIForm()
}

async function loadExternalSources() {
  await Promise.allSettled([
    loadCPAPools(),
    loadSub2APIServers(),
  ])
}

watch(settings, (value) => {
  if (!value) return
  const next = prepareSettingsForEdit(value)
  if (localSettings.value && savedSettingsBaseline.value && hasUnsavedSettings.value) {
    return
  }
  localSettings.value = next
  savedSettingsBaseline.value = prepareSettingsForEdit(next)
}, { immediate: true })

const reloadSettings = async () => {
  settingsLoadError.value = ''
  try {
    await settingsStore.loadSettings()
    await loadProxyRuntimeStatus(true)
  } catch (error: any) {
    settingsLoadError.value = error.message || '设置加载失败'
    toast.error(settingsLoadError.value)
  }
}

function shouldSkipActivatedReload() {
  return Boolean(
    hasUnsavedSettings.value ||
    isSaving.value ||
    settingsStore.isLoading ||
    imageStorageBusy.value ||
    proxyBusy.value ||
    proxyRuntimeTesting.value ||
    backupBusy.value ||
    savingExternalSource.value ||
    testingExternalSource.value ||
    userKeyBusy.value ||
    userKeyModal.value ||
    externalSourceModal.value,
  )
}

onMounted(async () => {
  await reloadSettings()
  await Promise.allSettled([
    loadUserKeys(),
    loadExternalSources(),
    loadBackups(),
  ])
})

onActivated(() => {
  if (!hasActivatedOnce) {
    hasActivatedOnce = true
    return
  }
  if (shouldSkipActivatedReload()) return
  void reloadSettings()
  void Promise.allSettled([
    loadUserKeys(),
    loadExternalSources(),
    loadBackups(),
  ])
})

const handleSave = async () => {
  if (!localSettings.value) return
  const confirmed = await confirmDialog.ask({
    title: '确认保存系统设置',
    message: '即将保存当前系统设置，可能影响接口地址、并发、存储和备份策略。是否继续？',
    confirmText: '保存',
    cancelText: '取消',
  })
  if (!confirmed) return

  isSaving.value = true

  try {
    await persistSettings(true)
  } catch (error: any) {
    toast.error(error.message || '保存失败')
  } finally {
    isSaving.value = false
  }
}
</script>

<style scoped>
.settings-check-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(13.5rem, 1fr));
  gap: 8px;
}

.settings-check-grid--single {
  grid-template-columns: minmax(0, 1fr);
}

.settings-check-item {
  min-height: 38px;
  border: 1px solid hsl(var(--border));
  border-radius: 14px;
  background: hsl(var(--background) / 0.72);
  transition:
    border-color 0.16s ease,
    background-color 0.16s ease;
}

.settings-check-item:hover {
  border-color: hsl(var(--foreground) / 0.18);
  background: hsl(var(--muted) / 0.24);
}

.settings-check-control {
  display: flex;
  min-height: 38px;
  align-items: center;
  gap: 8px;
  padding-right: 10px;
}

.settings-check-item :deep(label) {
  display: flex;
  width: 100%;
  flex: 1;
  min-height: 38px;
  align-items: center;
  gap: 10px;
  padding: 9px 11px;
}

.settings-check-item :deep(label > span:last-child) {
  color: hsl(var(--foreground) / 0.78);
  line-height: 1.35;
}

</style>
