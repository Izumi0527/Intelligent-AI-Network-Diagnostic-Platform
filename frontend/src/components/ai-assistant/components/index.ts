/**
 * AI助手子组件统一导出
 *
 * 仅提供命名导出。原先的 default 导出（barrel object）未被消费者使用，
 * 且会让 ESLint @typescript-eslint/no-unsafe-assignment 误判 .vue 模块为 error typed，
 * 故移除。
 */

import ChatHeader from './ChatHeader.vue';
import ModelSelector from './ModelSelector.vue';
import StreamToggle from './StreamToggle.vue';
import SearchToggle from './SearchToggle.vue';
import SearchSourcesBlock from './SearchSourcesBlock.vue';
import ChatMessages from './ChatMessages.vue';
import ChatInput from './ChatInput.vue';
import MessageActions from './MessageActions.vue';
import StopGenerationButton from './StopGenerationButton.vue';
import ConfirmDialog from './ConfirmDialog.vue';

export {
  ChatHeader,
  ModelSelector,
  StreamToggle,
  SearchToggle,
  SearchSourcesBlock,
  ChatMessages,
  ChatInput,
  MessageActions,
  StopGenerationButton,
  ConfirmDialog
};
