import { ref, type Ref } from 'vue';
import { useTerminalStore } from '@/stores/terminal';

interface UseCommandHistoryReturn {
  command: Ref<string>;
  showPrevious: () => void;
  showNext: () => void;
  reset: () => void;
}

/**
 * 终端命令输入框的本地 ref 与历史导航。
 *
 * 上键回溯到更早的命令，下键往回到更新的命令（直到清空）。
 * 历史栈本身由 terminal store 维护，本 composable 只做"当前输入框值"与
 * 历史调用之间的桥接，便于在 input 元素上 v-model。
 */
export function useCommandHistory(): UseCommandHistoryReturn {
  const store = useTerminalStore();
  const command = ref('');

  const showPrevious = (): void => {
    const prev = store.getPreviousCommand();
    if (prev !== undefined && prev !== '') { command.value = prev; }
  };

  const showNext = (): void => {
    const next = store.getNextCommand();
    command.value = next ?? '';
  };

  const reset = (): void => {
    command.value = '';
  };

  return { command, showPrevious, showNext, reset };
}
