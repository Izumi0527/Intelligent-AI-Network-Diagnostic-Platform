import type { ChatData, ChatMessage } from '@/types/chat';
import { logger } from './logger';

export const localStorageUtils = {
  saveChat(key: string, chatData: ChatData | ChatMessage[]): boolean {
    try {
      localStorage.setItem(key, JSON.stringify(chatData));
      return true;
    } catch (error) {
      logger.error('保存聊天记录失败:', error);
      return false;
    }
  },

  loadChat(key: string): ChatData | ChatMessage[] | null {
    try {
      const data = localStorage.getItem(key);
      return data !== null && data.length > 0 ? JSON.parse(data) as (ChatData | ChatMessage[]) : null;
    } catch (error) {
      logger.error('加载聊天记录失败:', error);
      return null;
    }
  },

  removeChat(key: string): boolean {
    try {
      localStorage.removeItem(key);
      return true;
    } catch (error) {
      logger.error('删除聊天记录失败:', error);
      return false;
    }
  },

  clearChat(key: string): boolean {
    try {
      localStorage.removeItem(key);
      return true;
    } catch (error) {
      logger.error('清除聊天记录失败:', error);
      return false;
    }
  },

  // 清除所有聊天记录
  clearAllChats(): boolean {
    try {
      const keys: string[] = [];
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key?.startsWith('chat_history_') === true) {
          keys.push(key);
        }
      }

      keys.forEach(key => localStorage.removeItem(key));
      return true;
    } catch (error) {
      logger.error('清除所有聊天记录失败:', error);
      return false;
    }
  },

  // 获取所有聊天记录
  getAllChats(): Record<string, ChatData | ChatMessage[]> {
    const chats: Record<string, ChatData | ChatMessage[]> = {};
    try {
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key?.startsWith('chat_history_') === true) {
          const chatData = this.loadChat(key);
          if (chatData) {
            chats[key] = chatData;
          }
        }
      }
    } catch (error) {
      logger.error('获取所有聊天记录失败:', error);
    }
    return chats;
  }
};