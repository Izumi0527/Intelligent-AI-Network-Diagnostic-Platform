/**
 * 通用图标统一出口
 *
 * 6 个图标统一以 SFC `.vue` 文件为单一真源（含 width / height /
 * stroke-width / stroke-linecap / stroke-linejoin / aria-hidden /
 * focusable 完整 attrs），通过本文件 re-export 为命名导出。
 *
 * 历史背景（plan G3 修复，2026-05-23）：
 * 旧实现在此处用 `defineComponent + h('svg', { strokeWidth: '2', ... })`
 * 重定义了 SunIcon / MoonIcon / SendIcon / ClearIcon，覆盖了 `.vue` 真源。
 * 由于 `h()` 调用使用 React 风格 camelCase 且漏传 width / height /
 * aria-hidden / focusable，导致运行时 DOM 上的 svg 缺失这些属性、
 * `stroke-width` 错位为无效的 `strokeWidth`。
 * 现统一回到 .vue 模板字面写法，使 ESLint / a11y / 视觉一致。
 */

export { default as ConnectIcon } from './ConnectIcon.vue';
export { default as DisconnectIcon } from './DisconnectIcon.vue';
export { default as SendIcon } from './SendIcon.vue';
export { default as ClearIcon } from './ClearIcon.vue';
export { default as SunIcon } from './SunIcon.vue';
export { default as MoonIcon } from './MoonIcon.vue';
export { default as ChevronDownIcon } from './ChevronDownIcon.vue';
export { default as SearchIcon } from './SearchIcon.vue';
