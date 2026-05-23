"""P6 收尾验证脚本：多视口 axe-core 审计 + 静态可达性 + Mobile/暗色截图归档。

仿 scripts/p3_axe_audit.py 扩展：
- 三视口跑 axe.run()：mobile 375、tablet 768、desktop 1280
- 每个视口的 static_audit：iconHiddenCount/iconCount 必须一致（"3/3 维持"）
- 4 张截图归档到 discuss/redesign-p6/：mobile-light、mobile-dark、tablet-light、desktop-dark
- 退出码：所有视口 violations 之和 = 0 且 iconHiddenCount == iconCount → 0；否则 1

依赖：系统 Python (Python312) 的 playwright 1.60.0；不依赖 backend venv。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

AXE_CDN = "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.2/axe.min.js"
APP_URL = "http://127.0.0.1:5173"
OUT_DIR = Path(__file__).resolve().parent.parent / "discuss" / "redesign-p6"
OUT_DIR.mkdir(parents=True, exist_ok=True)

VIEWPORTS = [
    {"name": "mobile-375", "size": (375, 667), "label": "iPhone SE mobile"},
    {"name": "tablet-768", "size": (768, 1024), "label": "iPad tablet"},
    {"name": "desktop-1280", "size": (1280, 800), "label": "Desktop"},
]


def run_axe(page) -> dict:
    page.add_script_tag(url=AXE_CDN)
    page.wait_for_function("typeof window.axe !== 'undefined'")
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
    """P6 关键 a11y 标记落地校验。"""
    return page.evaluate(
        """() => {
            const svgs = Array.from(document.querySelectorAll('svg'));
            const messageActionsCopy = document.querySelector('[aria-label="复制此消息"]');
            const messageActionsRetry = document.querySelector('[aria-label="重新发送"]');
            const chatInput = document.querySelector('#chat-message-input');
            const messageList = document.querySelector('.chat-messages');
            return {
                iconCount: svgs.length,
                iconHiddenCount: svgs.filter(s => s.getAttribute('aria-hidden') === 'true').length,
                logRoles: document.querySelectorAll('[role=\"log\"]').length,
                alertRoles: document.querySelectorAll('[role=\"alert\"]').length,
                statusRoles: document.querySelectorAll('[role=\"status\"]').length,
                ariaLive: document.querySelectorAll('[aria-live]').length,
                particlesAriaHidden: Boolean(document.querySelector('.floating-particles-bg .particles-layer[aria-hidden=\"true\"]')),
                messageListHasLogRole: messageList ? messageList.getAttribute('role') === 'log' : false,
                messageListAriaLive: messageList ? messageList.getAttribute('aria-live') : null,
                messageActionsCopyLabelOk: Boolean(messageActionsCopy),
                messageActionsRetryLabelOk: Boolean(messageActionsRetry),
                chatInputHasInvalidAttr: chatInput ? chatInput.hasAttribute('aria-invalid') : false,
                viewportWidth: window.innerWidth,
                viewportHeight: window.innerHeight,
                isDark: document.documentElement.classList.contains('dark')
            };
        }"""
    )


def set_dark_mode(page, enable: bool) -> None:
    """通过主题按钮切换暗色，必要时反复重试一次。"""
    cur = page.evaluate("() => document.documentElement.classList.contains('dark')")
    if cur == enable:
        return
    btn = page.locator('button[title*="模式"]').first
    btn.click()
    page.wait_for_timeout(250)


def interactive_regression(page) -> dict:
    """复用 P3 风格交互回归（不触达后端）。仅在 desktop 视口跑一次即可。"""
    results: dict[str, object] = {}
    try:
        page.fill('#terminal-device-address', '192.168.99.99')
        page.fill('#terminal-port', '22')
        page.fill('#terminal-username', 'auditor')
        page.fill('#terminal-password', 'pw-not-real')
        results['form_values'] = {
            'address': page.input_value('#terminal-device-address'),
            'port': page.input_value('#terminal-port'),
            'username': page.input_value('#terminal-username'),
        }
    except Exception as exc:
        results['form_values_error'] = str(exc)

    try:
        chat_input = page.locator('#chat-message-input')
        chat_input.click()
        chat_input.fill('hello p6 audit')
        results['chat_input_filled'] = chat_input.input_value()
        # Escape 清空（P5 新增）
        page.keyboard.press('Escape')
        page.wait_for_timeout(100)
        results['chat_input_after_escape'] = chat_input.input_value()
    except Exception as exc:
        results['chat_input_error'] = str(exc)

    try:
        before = page.evaluate("() => document.documentElement.classList.contains('dark')")
        set_dark_mode(page, not before)
        after = page.evaluate("() => document.documentElement.classList.contains('dark')")
        results['theme_toggle'] = {'before_dark': before, 'after_dark': after}
        # 复位
        set_dark_mode(page, before)
    except Exception as exc:
        results['theme_toggle_error'] = str(exc)

    return results


def audit_one_viewport(page, vp: dict, dark: bool) -> dict:
    page.set_viewport_size({"width": vp["size"][0], "height": vp["size"][1]})
    set_dark_mode(page, dark)
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(300)
    static = static_audit(page)
    axe = run_axe(page)
    return {
        "name": f"{vp['name']}-{'dark' if dark else 'light'}",
        "size": list(vp["size"]),
        "dark": dark,
        "violation_count": len(axe['violations']),
        "violations": axe['violations'],
        "incomplete": axe['incomplete'],
        "passes": axe['passes'],
        "inapplicable": axe['inapplicable'],
        "static": static,
    }


def screenshot(page, vp: dict, dark: bool, filename: str) -> dict:
    page.set_viewport_size({"width": vp["size"][0], "height": vp["size"][1]})
    set_dark_mode(page, dark)
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(400)
    out_path = OUT_DIR / filename
    page.screenshot(path=str(out_path), full_page=True)
    size = out_path.stat().st_size
    return {"file": filename, "bytes": size, "exists": out_path.exists()}


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.goto(APP_URL, wait_until='networkidle')
            page.reload(wait_until='networkidle')

            # 桌面视口交互回归（含暗色切换冒烟）
            page.set_viewport_size({"width": 1280, "height": 800})
            interactive = interactive_regression(page)

            # 多视口 axe + static 审计
            audits: list[dict] = []
            audits.append(audit_one_viewport(page, VIEWPORTS[0], dark=False))   # mobile light
            audits.append(audit_one_viewport(page, VIEWPORTS[0], dark=True))    # mobile dark
            audits.append(audit_one_viewport(page, VIEWPORTS[1], dark=False))   # tablet light
            audits.append(audit_one_viewport(page, VIEWPORTS[2], dark=True))    # desktop dark
            # 复位 light
            set_dark_mode(page, False)

            # 4 张截图
            shots: list[dict] = []
            shots.append(screenshot(page, VIEWPORTS[0], dark=False, filename="p6-mobile-375.png"))
            shots.append(screenshot(page, VIEWPORTS[0], dark=True, filename="p6-mobile-dark.png"))
            shots.append(screenshot(page, VIEWPORTS[1], dark=False, filename="p6-tablet-768.png"))
            shots.append(screenshot(page, VIEWPORTS[2], dark=True, filename="p6-dark-full.png"))

            total_violations = sum(a['violation_count'] for a in audits)
            icon_ok_all = all(a['static']['iconHiddenCount'] == a['static']['iconCount'] for a in audits)
            # 截图非空判定：mobile 视口 PNG 自然偏小（~40-50 KB），desktop 偏大（~90 KB）。
            # 阈值 20 KB 既能挡空白图（典型 <5 KB），又不误杀正常 mobile 截图。
            shots_ok = all(s['exists'] and s['bytes'] > 20_000 for s in shots)

            report = {
                "app_url": APP_URL,
                "viewports": audits,
                "total_violation_count": total_violations,
                "icon_a11y_maintained": icon_ok_all,
                "screenshots": shots,
                "screenshots_ok": shots_ok,
                "interactive_regression": interactive,
            }

            out_path = OUT_DIR / 'p6-axe-report.json'
            out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

            print(f"[ok] wrote {out_path}")
            print(f"[axe] total_violations={total_violations}")
            print(f"[a11y] icon_a11y_maintained={icon_ok_all}")
            for a in audits:
                s = a['static']
                print(
                    f"  [{a['name']}] violations={a['violation_count']} "
                    f"icons={s['iconHiddenCount']}/{s['iconCount']} "
                    f"log={s['logRoles']} alert={s['alertRoles']} aria-live={s['ariaLive']}"
                )
            for s in shots:
                tag = "ok" if s['exists'] and s['bytes'] > 20_000 else "warn"
                kb = s['bytes'] / 1024
                print(f"  [shot:{tag}] {s['file']} {kb:.1f} KB")

            if total_violations == 0 and icon_ok_all and shots_ok:
                return 0
            return 1
        finally:
            browser.close()


if __name__ == '__main__':
    sys.exit(main())
