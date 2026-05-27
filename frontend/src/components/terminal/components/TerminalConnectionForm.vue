<template>
  <form class="terminal-form" @submit.prevent="handleConnect">
    <div class="terminal-form__field">
      <label for="terminal-connection-type" class="terminal-form__label">连接方式</label>
      <select
        id="terminal-connection-type"
        v-model="store.connectionType"
        name="connectionType"
        class="terminal-config-input terminal-form__select"
      >
        <option value="telnet">Telnet</option>
        <option value="ssh">SSH</option>
      </select>
    </div>

    <div class="terminal-form__field">
      <label for="terminal-device-address" class="terminal-form__label">设备地址</label>
      <input
        id="terminal-device-address"
        v-model="store.deviceAddress"
        name="deviceAddress"
        class="terminal-config-input terminal-form__input"
        placeholder="192.168.20.1"
        type="text"
        autocomplete="off"
      />
    </div>

    <div class="terminal-form__field terminal-form__field--narrow">
      <label for="terminal-port" class="terminal-form__label">端口</label>
      <input
        id="terminal-port"
        v-model="store.port"
        name="port"
        class="terminal-config-input terminal-form__input"
        :placeholder="store.connectionType === 'ssh' ? '22' : '23'"
        type="number"
        inputmode="numeric"
        autocomplete="off"
      />
    </div>

    <div class="terminal-form__field">
      <label for="terminal-username" class="terminal-form__label">用户名</label>
      <input
        id="terminal-username"
        v-model="store.username"
        name="username"
        class="terminal-config-input terminal-form__input"
        placeholder="admin"
        type="text"
        autocomplete="username"
      />
    </div>

    <div class="terminal-form__field">
      <label for="terminal-password" class="terminal-form__label">密码</label>
      <input
        id="terminal-password"
        v-model="store.password"
        name="password"
        class="terminal-config-input terminal-form__input"
        type="password"
        placeholder="••••••••"
        autocomplete="current-password"
      />
    </div>

    <div class="terminal-form__field terminal-form__field--actions">
      <span class="terminal-form__label">&nbsp;</span>
      <div class="terminal-form__btn-group">
        <button
          type="submit"
          class="terminal-config-button"
          :class="{ 'terminal-config-button--danger': store.connectionStatus === 'connected' }"
          :disabled="store.connectionStatus === 'connecting' && !store.canCancelConnection"
        >
          <span v-if="store.connectionStatus === 'connecting' && !store.canCancelConnection">
            连接中…
          </span>
          <span v-else>{{ store.connectionStatus === 'connected' ? '断开' : '连接' }}</span>
        </button>

        <button
          v-if="store.canCancelConnection && store.connectionStatus === 'connecting'"
          type="button"
          class="terminal-config-button terminal-config-button--cancel"
          @click="handleCancelConnect"
        >
          取消
        </button>
      </div>
    </div>
  </form>
</template>

<script setup lang="ts">
import { useTerminalStore } from '@/stores/terminal';

const store = useTerminalStore();

const handleConnect = async (): Promise<void> => {
  await store.connectToDevice();
};

const handleCancelConnect = async (): Promise<void> => {
  await store.cancelConnection();
};
</script>

<style scoped>
.terminal-form {
  display: grid;
  grid-template-columns: 110px 1fr 80px 1fr 1fr 110px;
  gap: 10px;
  align-items: end;
}

.terminal-form__field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.terminal-form__field--narrow {
  max-width: 100px;
}

.terminal-form__field--actions .terminal-form__btn-group {
  display: flex;
  gap: 6px;
}

.terminal-form__label {
  font-size: 10.5px;
  font-family: var(--app-font-mono);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: color-mix(in oklch, var(--terminal-fg) 55%, transparent);
}

.terminal-form__select,
.terminal-form__input {
  width: 100%;
}

.terminal-config-button--danger {
  background-color: var(--destructive);
  border-color: color-mix(in oklch, var(--destructive), black 8%);
}

.terminal-config-button--danger:hover:not(:disabled) {
  background-color: color-mix(in oklch, var(--destructive), white 6%);
}

.terminal-config-button--cancel {
  background-color: var(--warning);
  color: var(--warning-foreground);
  border-color: color-mix(in oklch, var(--warning), black 8%);
}

.terminal-config-button--cancel:hover:not(:disabled) {
  background-color: color-mix(in oklch, var(--warning), white 6%);
}

@media (max-width: 1024px) {
  .terminal-form {
    grid-template-columns: repeat(3, 1fr);
  }
  .terminal-form__field--narrow {
    max-width: none;
  }
}

@media (max-width: 768px) {
  .terminal-form {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
