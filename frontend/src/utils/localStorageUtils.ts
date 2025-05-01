export const localStorageUtils = {
    saveChat(key: string, chatData: any) {
        try {
            localStorage.setItem(key, JSON.stringify(chatData));
        } catch (error) {
            console.error('保存聊天记录失败:', error);
        }
    },

    loadChat(key: string) {
        try {
            const data = localStorage.getItem(key);
            return data ? JSON.parse(data) : null;
        } catch (error) {
            console.error('加载聊天记录失败:', error);
            return null;
        }
    },

    clearChat(key: string) {
        localStorage.removeItem(key);
    },

    // 清除所有聊天记录
    clearAllChats() {
        const keys = [];
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (key && key.startsWith('chat_history_')) {
                keys.push(key);
            }
        }

        keys.forEach(key => localStorage.removeItem(key));
    }
}; 