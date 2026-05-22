<template>
  <form @submit.prevent="handleConnect" class="grid grid-cols-6 gap-4">
    <!-- 1. 连接方式 -->
    <div>
      <label for="terminal-connection-type" class="text-sm font-medium mb-1 block text-gray-400">连接方式</label>
      <select
        id="terminal-connection-type"
        name="connectionType"
        v-model="store.connectionType"
        class="w-full rounded-lg border terminal-config-input px-3 py-2 text-sm transition-[transform,opacity,background-color,border-color,box-shadow,color] duration-[var(--dur-base)] ease-[var(--ease-out)] hover:border-primary/50"
      >
        <option value="telnet">Telnet</option>
        <option value="ssh">SSH</option>
      </select>
    </div>

    <!-- 2. 设备地址 -->
    <div>
      <label for="terminal-device-address" class="text-sm font-medium mb-1 block text-gray-400">设备地址</label>
      <input
        id="terminal-device-address"
        name="deviceAddress"
        v-model="store.deviceAddress"
        class="w-full rounded-lg border terminal-config-input px-3 py-2 text-sm transition-[transform,opacity,background-color,border-color,box-shadow,color] duration-[var(--dur-base)] ease-[var(--ease-out)] hover:border-primary/50 focus:border-primary"
        placeholder="192.168.20.1"
        type="text"
        autocomplete="off"
      />
    </div>

    <!-- 3. 端口 -->
    <div>
      <label for="terminal-port" class="text-sm font-medium mb-1 block text-gray-400">端口</label>
      <input
        id="terminal-port"
        name="port"
        v-model="store.port"
        class="w-20 rounded-lg border terminal-config-input px-3 py-2 text-sm transition-[transform,opacity,background-color,border-color,box-shadow,color] duration-[var(--dur-base)] ease-[var(--ease-out)] hover:border-primary/50 focus:border-primary"
        :placeholder="store.connectionType === 'ssh' ? '22' : '23'"
        type="number"
        inputmode="numeric"
        autocomplete="off"
      />
    </div>

    <!-- 4. 用户名 -->
    <div>
      <label for="terminal-username" class="text-sm font-medium mb-1 block text-gray-400">用户名</label>
      <input
        id="terminal-username"
        name="username"
        v-model="store.username"
        class="w-full rounded-lg border terminal-config-input px-3 py-2 text-sm transition-[transform,opacity,background-color,border-color,box-shadow,color] duration-[var(--dur-base)] ease-[var(--ease-out)] hover:border-primary/50 focus:border-primary"
        placeholder="admin"
        type="text"
        autocomplete="username"
      />
    </div>

    <!-- 5. 密码 -->
    <div>
      <label for="terminal-password" class="text-sm font-medium mb-1 block text-gray-400">密码</label>
      <input
        id="terminal-password"
        name="password"
        v-model="store.password"
        class="w-full rounded-lg border terminal-config-input px-3 py-2 text-sm transition-[transform,opacity,background-color,border-color,box-shadow,color] duration-[var(--dur-base)] ease-[var(--ease-out)] hover:border-primary/50 focus:border-primary"
        type="password"
        placeholder="••••••••"
        autocomplete="current-password"
      />
    </div>

    <!-- 6. 执行 / 取消 -->
    <div class="flex items-end">
      <div class="w-full flex gap-2">
        <button
          type="submit"
          :class="[
            'flex-1 h-10 terminal-config-button rounded-lg font-medium text-sm',
            store.connectionStatus === 'connected'
              ? 'bg-red-600 hover:bg-red-700'
              : 'terminal-config-button'
          ]"
          :disabled="store.connectionStatus === 'connecting' && !store.canCancelConnection"
        >
          <div class="flex items-center justify-center">
            <span
              v-if="store.connectionStatus === 'connecting' && !store.canCancelConnection"
              class="pulse-animation"
            >连接中...</span>
            <span v-else>{{ store.connectionStatus === 'connected' ? '断开连接' : '执行连接' }}</span>
          </div>
        </button>

        <button
          v-if="store.canCancelConnection && store.connectionStatus === 'connecting'"
          type="button"
          class="h-10 px-4 bg-yellow-600 hover:bg-yellow-700 text-white rounded-lg font-medium text-sm transition-[transform,opacity,background-color,border-color,box-shadow,color] duration-[var(--dur-base)] ease-[var(--ease-out)]"
          @click="handleCancelConnect"
        >
          取消连接
        </button>
      </div>
    </div>
  </form>
</template>

<script setup lang="ts">
import { useTerminalStore } from '@/stores/terminal'

const store = useTerminalStore()

const handleConnect = async (): Promise<void> => {
  await store.connectToDevice()
}

const handleCancelConnect = async (): Promise<void> => {
  await store.cancelConnection()
}
</script>
