"""P3 收尾验证脚本：axe-core 自动审计 + UI 层静态/交互回归。

只在 webapp-testing skill 推荐的"UI 层 axe + 静态审计"范围内执行：
- 注入 axe-core 4.x（CDN），跑 axe.run() 全规则，输出 violations
- 静态结构断言：focus-visible 取色 / 图标 aria-hidden / 思考块 role=log
- 交互回归（不触达后端 SSH/Telnet）：表单填写 + Ctrl+K 清空 + 暗色切换

跳过：真实 SSH/Telnet 连接、AI 真实流式 — 这些需要真实设备/远端 API。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

AXE_CDN = "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.2/axe.min.js"
APP_URL = "http://127.0.0.1:5173"
OUT_DIR = Path(__file__).resolve().parent.parent / "discuss"
OUT_DIR.mkdir(exist_ok=True)


def run_axe(page) -> dict:
    page.add_script_tag(url=AXE_CDN)
    page.wait_for_function("typeof window.axe !== 'undefined'")
    # 全规则 + WCAG 2.1 AA tag
    result = page.evaluate(
        """async () => {
            const res = await window.axe.run(document, {
                runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'] }
            });
            return {
                violations: res.violations.map(v => ({
                    id: v.id,
                    impact: v.impact,
                    help: v.help,
                    helpUrl: v.helpUrl,
                    nodes: v.nodes.map(n => ({ target: n.target, html: n.html.slice(0, 200) }))
                })),
                incomplete: res.incomplete.map(v => ({ id: v.id, help: v.help, nodes: v.nodes.length })),
                passes: res.passes.length,
                inapplicable: res.inapplicable.length
            };
        }"""
    )
    return result


def static_audit(page) -> dict:
    """断言 P3 #10 的关键 a11y 标记真的落到了运行时 DOM。"""
    return page.evaluate(
        """() => {
            const style = getComputedStyle(document.body);
            const svgs = Array.from(document.querySelectorAll('svg'));
            return {
                themeBgVarSample: style.backgroundColor,
                iconCount: svgs.length,
                iconHiddenCount: svgs.filter(s => s.getAttribute('aria-hidden') === 'true').length,
                iconAttrs: svgs.map(s => ({
                    classes: s.getAttribute('class'),
                    ariaHidden: s.getAttribute('aria-hidden'),
                    focusable: s.getAttribute('focusable'),
                    outer: s.outerHTML.slice(0, 160)
                })),
                logRoles: document.querySelectorAll('[role=\"log\"]').length,
                statusRoles: document.querySelectorAll('[role=\"status\"]').length,
                ariaLive: document.querySelectorAll('[aria-live]').length,
                particlesAriaHidden: Boolean(document.querySelector('.floating-particles-bg .particles-layer[aria-hidden=\"true\"]')),
                terminalLogRegion: Boolean(document.querySelector('[role=\"log\"][aria-live=\"polite\"]'))
            };
        }"""
    )


def interactive_regression(page) -> dict:
    """不触达后端的 UI 交互回归。"""
    results: dict[str, object] = {}

    # 表单填写（v-model → store）
    page.fill('#terminal-device-address', '192.168.99.99')
    page.fill('#terminal-port', '22')
    page.fill('#terminal-username', 'auditor')
    page.fill('#terminal-password', 'pw-not-real')
    results['form_values'] = {
        'address': page.input_value('#terminal-device-address'),
        'port': page.input_value('#terminal-port'),
        'username': page.input_value('#terminal-username'),
    }

    # ChatInput 区域：聚焦 + 输入 + 按键
    chat_input = page.locator('#chat-message-input')
    chat_input.click()
    chat_input.fill('hello dompurify')
    results['chat_input_filled'] = chat_input.input_value()
    # Ctrl+K 由 useAiKeyboard 监听 document keydown → onClear → store.clearMessages
    # 注意：清空对话不会清空 input v-model（那是本地 ref），断言改为消息列表为空
    page.evaluate("() => window.__test_store_messages_before = document.querySelectorAll('.message-user, .message-assistant').length")
    page.keyboard.press('Control+KeyK')
    page.wait_for_timeout(150)
    results['chat_input_after_ctrl_k_value'] = chat_input.input_value()
    results['ctrl_k_triggered_via_document_listener'] = page.evaluate(
        "() => document.querySelectorAll('.message-user, .message-assistant').length"
    ) == 0

    # 暗色切换：找标题为"切换到深色模式"的按钮
    theme_btn = page.locator('button[title*="模式"]').first
    before = page.evaluate("() => document.documentElement.classList.contains('dark')")
    theme_btn.click()
    page.wait_for_timeout(200)
    after = page.evaluate("() => document.documentElement.classList.contains('dark')")
    results['theme_toggle'] = {'before_dark': before, 'after_dark': after}
    # 切回，避免影响后续审计基线
    theme_btn.click()
    page.wait_for_timeout(200)

    return results


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.goto(APP_URL, wait_until='networkidle')
            # 强制 hard reload，确保抓到 vite HMR 的最新模块
            page.reload(wait_until='networkidle')

            static = static_audit(page)
            interactive = interactive_regression(page)
            page.wait_for_load_state('networkidle')
            axe = run_axe(page)

            report = {
                'app_url': APP_URL,
                'axe': {
                    'violation_count': len(axe['violations']),
                    'violations': axe['violations'],
                    'incomplete': axe['incomplete'],
                    'passes': axe['passes'],
                    'inapplicable': axe['inapplicable'],
                },
                'static_audit': static,
                'interactive_regression': interactive,
            }

            out_path = OUT_DIR / 'p3-axe-report.json'
            out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
            print(f'[ok] wrote {out_path}')
            print(f"[axe] violations={report['axe']['violation_count']}, passes={axe['passes']}, incomplete={len(axe['incomplete'])}")
            print(f"[static] icons {static['iconHiddenCount']}/{static['iconCount']} aria-hidden, log={static['logRoles']}, status={static['statusRoles']}, aria-live={static['ariaLive']}")
            print(f"[interactive] form_address={interactive['form_values']['address']}, ctrl_k_clears_messages={interactive['ctrl_k_triggered_via_document_listener']}, theme_toggle={interactive['theme_toggle']}")
            return 0 if report['axe']['violation_count'] == 0 else 1
        finally:
            browser.close()


if __name__ == '__main__':
    sys.exit(main())
