import { defineComponent, h } from 'vue';
import ConnectIcon from './ConnectIcon.vue';
import DisconnectIcon from './DisconnectIcon.vue';

// 发送图标
export const SendIcon = defineComponent({
    name: 'SendIcon',
    setup() {
        return () => h('svg', {
            xmlns: 'http://www.w3.org/2000/svg',
            viewBox: '0 0 24 24',
            fill: 'none',
            stroke: 'currentColor',
            strokeWidth: '2',
            strokeLinecap: 'round',
            strokeLinejoin: 'round',
        }, [
            h('path', { d: 'M22 2L11 13' }),
            h('path', { d: 'M22 2L15 22L11 13L2 9L22 2Z' }),
        ]);
    },
});

// 清除图标
export const ClearIcon = defineComponent({
    name: 'ClearIcon',
    setup() {
        return () => h('svg', {
            xmlns: 'http://www.w3.org/2000/svg',
            viewBox: '0 0 24 24',
            fill: 'none',
            stroke: 'currentColor',
            strokeWidth: '2',
            strokeLinecap: 'round',
            strokeLinejoin: 'round',
        }, [
            h('path', { d: 'M3 6H21' }),
            h('path', { d: 'M19 6V20C19 21 18 22 17 22H7C6 22 5 21 5 20V6' }),
            h('path', { d: 'M8 6V4C8 3 9 2 10 2H14C15 2 16 3 16 4V6' }),
            h('path', { d: 'M10 11V17' }),
            h('path', { d: 'M14 11V17' }),
        ]);
    },
});

// 太阳图标（明亮模式）
export const SunIcon = defineComponent({
    name: 'SunIcon',
    setup() {
        return () => h('svg', {
            xmlns: 'http://www.w3.org/2000/svg',
            viewBox: '0 0 24 24',
            fill: 'none',
            stroke: 'currentColor',
            strokeWidth: '2',
            strokeLinecap: 'round',
            strokeLinejoin: 'round',
        }, [
            h('circle', { cx: '12', cy: '12', r: '5' }),
            h('line', { x1: '12', y1: '1', x2: '12', y2: '3' }),
            h('line', { x1: '12', y1: '21', x2: '12', y2: '23' }),
            h('line', { x1: '4.22', y1: '4.22', x2: '5.64', y2: '5.64' }),
            h('line', { x1: '18.36', y1: '18.36', x2: '19.78', y2: '19.78' }),
            h('line', { x1: '1', y1: '12', x2: '3', y2: '12' }),
            h('line', { x1: '21', y1: '12', x2: '23', y2: '12' }),
            h('line', { x1: '4.22', y1: '19.78', x2: '5.64', y2: '18.36' }),
            h('line', { x1: '18.36', y1: '5.64', x2: '19.78', y2: '4.22' }),
        ]);
    },
});

// 月亮图标（暗黑模式）
export const MoonIcon = defineComponent({
    name: 'MoonIcon',
    setup() {
        return () => h('svg', {
            xmlns: 'http://www.w3.org/2000/svg',
            viewBox: '0 0 24 24',
            fill: 'none',
            stroke: 'currentColor',
            strokeWidth: '2',
            strokeLinecap: 'round',
            strokeLinejoin: 'round',
        }, [
            h('path', { d: 'M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z' }),
        ]);
    },
});

export {
    ConnectIcon,
    DisconnectIcon
}; 