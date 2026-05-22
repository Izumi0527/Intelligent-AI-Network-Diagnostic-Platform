# G3 — Vue 3.5 SVG aria-hidden 漂移点彻底解决

> 范围：plan `lint-1600-svg-aria-hidden-partitioned-pebble.md` Phase G3
> 实施日期：2026-05-23
> 单 commit 修复，触动 1 个文件 / +30 / -91 行

---

## 1. 背景（P3 遗留漂移点）

P3 #10 commit message 记录"全部图标 svg 添加 aria-label 或 aria-hidden"
在运行时未真正落实——`scripts/p3_axe_audit.py` 输出的 `static_audit.iconHiddenCount`
为 `0/3`，三个项目图标的 svg DOM 完全没有 `aria-hidden / focusable / width /
height` 属性，且 `stroke-width="2"` 被错位为 HTML 中无效的 `strokeWidth="2"`
(camelCase)。

axe 因父按钮（含 `aria-label` / `title`）的可达名称兜底而未报 violation，
故 P3 阶段以"已知漂移、留作 G3 处理"暂时收口。

## 2. plan 原始假设 vs 实际诊断

### plan agent 摸底假设（错误方向）

plan 把根因定位到 **Vue 3.5 runtime-dom `patchProp` 对 SVG 元素的 quirk**：

- `node_modules/vue/dist/.../runtime-dom` 第 777 行 `shouldSetAsProp(el, key, value, isSVG=true)`
- 第 797-804 行 SVG 分支应 fallback 到 `patchAttr()`（setAttribute）
- 但实测 aria-hidden 未写入，"报告内在矛盾"

并准备了 4 种 work-around（W1 字面、W2 动态绑定、W3 inheritAttrs:false +
v-bind="$attrs"、W4 onVnodeMounted setAttribute）做 PoC。

### G3.1 PoC 实际结果（推翻假设）

新建 `frontend/src/components/_debug/SvgQuirkProbe.vue` 含 4 种写法，临时挂
到 MainLayout，用 Playwright MCP 直接读取运行时 DOM：

| 写法 | aria-hidden | focusable | stroke-width | width/height |
|---|---|---|---|---|
| W1 模板字面 | ✅ "true" | ✅ "false" | ✅ "2" (kebab) | ✅ "24" |
| W2 动态绑定 | ✅ "true" | ✅ "false" | ✅ "2" (kebab) | ✅ "24" |
| W3 对象 v-bind | ✅ "true" | ✅ "false" | ✅ "2" (kebab) | ✅ "24" |
| W4 vnode-mounted hook | ✅ "true" | ✅ "false" | ✅ "2" (kebab) | ✅ "24" |

**4 种写法全部 work**。Vue 3.5.13 patchProp 对 SVG 属性的处理**完全正常**，
plan 的 quirk 假设不成立。

> 顺带发现：`@vnode-*` 钩子在 Vue 3.4+ 已废弃为 `@vue:*`，PoC W4 初版报
> 编译错误后改正。

## 3. 真正的根因

对比 PoC svg 与现有 6 个 `icons/*.vue` 的运行时 DOM，定位差异：

| svg 来源 | width/height | aria-hidden | stroke-width | strokeWidth (camel) |
|---|---|---|---|---|
| PoC W1-W4 | ✅ "24" | ✅ "true" | ✅ "2" | null（正确）|
| 6 个 `icons/*.vue` | **null（丢失）** | **null** | **null** | **"2"（错位）** |

**关键观察**：6 个 icon svg 在 DOM 上的 `outerHTML` 显示 `strokeWidth="2"`
（无效的 camelCase HTML attr），同时**完全没有** `width / height / aria-hidden /
focusable / stroke-linecap / stroke-linejoin`。

进一步审查 `frontend/src/components/common/icons/index.ts`：

```typescript
export const SunIcon = defineComponent({
  name: 'SunIcon',
  setup() {
    return (): VNode => h('svg', {
      xmlns: 'http://www.w3.org/2000/svg',
      viewBox: '0 0 24 24',
      fill: 'none',
      stroke: 'currentColor',
      strokeWidth: '2',         // React 风格 camelCase
      strokeLinecap: 'round',   // 漏传 width / height
      strokeLinejoin: 'round',  // 漏传 aria-hidden / focusable
    }, [ /* paths */ ]);
  },
});
```

`index.ts` 用 `defineComponent + h()` **重定义**了 `SunIcon / MoonIcon /
SendIcon / ClearIcon`，**覆盖**了同目录下对应的 `.vue` 单文件组件（这 4 个
`.vue` 文件其实是死代码——格式完美的模板字面 svg，无人消费）。

- `h()` 是运行时函数，attrs 原样 `setAttribute`，camelCase key 进入 HTML
  namespace 时是无效属性
- 漏传的属性根本不存在于运行时 vnode props，自然不会出现在 DOM

**这不是 Vue 3.5 quirk**，是项目内部 dual-source 实现（`.vue` 真源 vs
`.ts` h() 重定义）选错了源 + 写错了 key case。

## 4. 修复方案（commit #27）

放弃 plan 假设的 4 种 SFC 改写方案，改为统一图标真源：

```typescript
// frontend/src/components/common/icons/index.ts（修复后）
export { default as ConnectIcon } from './ConnectIcon.vue';
export { default as DisconnectIcon } from './DisconnectIcon.vue';
export { default as SendIcon } from './SendIcon.vue';
export { default as ClearIcon } from './ClearIcon.vue';
export { default as SunIcon } from './SunIcon.vue';
export { default as MoonIcon } from './MoonIcon.vue';
```

- 删除 4 个 `defineComponent + h()` 重定义
- 改为 re-export 6 个 SFC（保留 ConnectIcon / DisconnectIcon 原有 re-export 模式）
- 6 个 `.vue` 文件**不动**（模板写法已是 PoC W1 验证的正确写法）
- 3 个消费方（MainLayout / ChatHeader / ChatInput）**零修改**（仍是 named import）

## 5. G3.3 axe 闭环验证

修复后跑 axe + static_audit（通过 Playwright MCP 等价 `scripts/p3_axe_audit.py` 的核心逻辑）：

| 指标 | 修复前 | 修复后 | plan 标准 |
|---|---|---|---|
| `axe.violation_count` | 0 | 0 | =0 ✅ |
| `axe.passes` | 23 | 23 | 维持 ✅ |
| `axe.incomplete` (color-contrast) | 5 | 5 | plan 预期 |
| `iconHiddenCount / iconCount` | **0/3** | **3/3** | N/N ✅ |
| icon `aria-hidden` | null | "true" | "true" ✅ |
| icon `focusable` | null | "false" | "false" ✅ |
| icon `stroke-width` (kebab) | null | "2" | 合法 ✅ |
| icon `strokeWidth` (camel, 错位) | "2" | — | 已消除 ✅ |
| icon `width / height` | 丢失 | "24" / "24" | 真实落地 ✅ |

报告写入 `discuss/p3-axe-report.json`，含 `audit_history` 字段标注修复前后对比。

## 6. 验证矩阵

| 检查项 | 结果 |
|---|---|
| `npm run typecheck` | 0 error ✅ |
| `npm run lint` | 0 problems ✅ |
| `npm run build` | 1.02s success / 148 modules / dist 体积 +0.5% ✅ |
| `git status` | PoC 文件已清理，工作区干净 ✅ |
| PoC 临时引入回滚 | `MainLayout.vue` 已复原 ✅ |

## 7. 经验沉淀

1. **PoC 优先于猜测**：plan 给的根因假设（Vue runtime quirk）**完全错**。
   30 分钟的 PoC 实测直接推翻了"必须改 6 个 SFC + 多种写法切换"的设想，
   把范围从 ~60 行 diff（plan 估算）缩小到 1 个文件 30 行。
2. **运行时 DOM 是唯一真相**：基线 audit 中 `strokeWidth="2"` 这个细节
   就是定位线索——`.vue` 模板字面用 `stroke-width` 不可能产出 `strokeWidth`，
   说明 svg 并非由模板渲染，必有运行时构造（`h()`）参与。
3. **避免 dual-source**：`.vue` 与 `.ts h()` 同时提供同名导出是反模式。
   修复后所有图标走单一 SFC 真源，未来视觉/可达性调整都在 `.vue` 模板，
   不会再出现"改了一个地方不生效"。

## 8. 不在范围

- 后端架构边界测试 `test_models_layer_must_not_import_logger` 失败（独立任务）
- P3 incomplete 的 5 处 color-contrast（plan 已注明为"需要人工目测"项）
- `scripts/dev.*` / `scripts/backend-check.*` / docs 残留改动（独立任务）
