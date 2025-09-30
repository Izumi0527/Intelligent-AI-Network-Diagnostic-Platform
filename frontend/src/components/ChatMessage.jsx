/**
 * 彻底清理SSE消息中的所有data:前缀，并提取实际内容
 * @param {string} chunk - 原始的SSE消息块
 * @returns {string} - 清理后的文本内容
 */
const parseSSEChunk = (chunk) => {
  // 确保输入是字符串
  if (!chunk || typeof chunk !== 'string') {
    return '';
  }

  // 首先检查是否包含特定的错误字符串
  if (chunk.includes('unexpected keyword argument') || 
      chunk.includes('Client.request()') || 
      chunk.includes('Client.post()') ||
      chunk.includes('TypeError:')) {
    console.warn('检测到API内部错误，提取核心错误信息');
    
    // 移除所有data:前缀
    let cleanedError = chunk.replace(/data:/g, '');
    
    // 提取具体错误信息
    const typeErrorMatch = cleanedError.match(/TypeError:\s*([^]+?)(?:Traceback|\n\n|$)/);
    if (typeErrorMatch && typeErrorMatch[1]) {
      return `服务器内部错误: ${typeErrorMatch[1].trim()}`;
    }
    
    // 如果匹配不到具体TypeError，返回一个友好的错误信息
    return '服务器内部错误，请稍后再试或联系管理员';
  }

  // 检查是否存在严重的data:前缀污染
  const dataCount = (chunk.match(/data:/g) || []).length;
  
  // 如果存在大量data:标记或在内容中存在data:
  if (dataCount > 3 || (dataCount > 0 && /[^:]data:/.test(chunk))) {
    console.warn(`检测到data:前缀污染，共${dataCount}个前缀，尝试彻底清理`);
    
    // 首先，提取纯中文和英文内容 - 这是最安全的方法
    const contentRegex = /[\u4e00-\u9fa5A-Za-z0-9.,?!，。？！：:;；""''（）()\s]+/g;
    const matches = chunk.match(contentRegex);
    if (matches && matches.length > 0) {
      // 将所有匹配的内容连接起来
      let extractedContent = matches.join(' ').replace(/\s+/g, ' ').trim();
      
      // 再次确保没有data:前缀
      extractedContent = extractedContent.replace(/data:/g, '');
      
      if (extractedContent.length > 2) {
        console.log('使用内容提取策略处理严重污染数据');
        return extractedContent;
      }
    }
    
    // 如果上面的方法失败，使用更激进的清理方式
    let cleaner = chunk;
    
    // 1. 先整体替换所有data:
    cleaner = cleaner.replace(/data:/g, '');
    
    // 2. 去除可能的其他控制字符和多余空格
    cleaner = cleaner.replace(/\[DONE\]/g, '')
                    .replace(/\{\}/g, '')
                    .replace(/\s+/g, ' ')
                    .trim();
    
    if (cleaner) {
      console.log('使用激进清理策略处理data:污染');
      return cleaner;
    }
  }

  // 常规处理步骤
  let cleanedText = chunk;
  
  // 递进式清理所有data:前缀，无论它们出现在哪里
  cleanedText = cleanedText.replace(/data:/g, '');
  
  // 处理数据块分割
  const blocks = cleanedText.split('\n\n').filter(block => block.trim());
  if (blocks.length === 0) {
    blocks.push(cleanedText);
  }
  
  // 处理每个数据块
  let result = '';
  for (const block of blocks) {
    // 移除多余的空白和换行符
    let processedBlock = block.split('\n')
      .map(line => line.trim())
      .filter(line => line && line !== '[DONE]' && line !== '{}')
      .join(' ');
    
    // 尝试作为JSON解析
    try {
      const jsonData = JSON.parse(processedBlock);
      
      // 处理各种可能的JSON格式
      if (jsonData.content) {
        result += jsonData.content;
      } else if (jsonData.error) {
        // 专门处理错误消息
        result += `错误: ${jsonData.error}`;
      } else if (jsonData.choices && jsonData.choices.length > 0) {
        const choice = jsonData.choices[0];
        if (choice.delta && choice.delta.content) {
          result += choice.delta.content;
        } else if (choice.message && choice.message.content) {
          result += choice.message.content;
        } else if (typeof choice.text === 'string') {
          result += choice.text;
        }
      } else if (typeof jsonData === 'string') {
        // 有些API返回纯文本JSON字符串
        result += jsonData;
      } else {
        // 未识别的JSON结构，但不包含error字段时，可以考虑使用原始内容
        if (!jsonData.error) {
          // 过滤掉可能的控制字符和格式信息
          const filteredText = processedBlock
            .replace(/\[DONE\]/g, '')
            .replace(/\{\}/g, '')
            .replace(/[\[\]{}]/g, ' ')
            .replace(/\s+/g, ' ')
            .trim();
          
          if (filteredText) {
            result += filteredText + ' ';
          }
        }
      }
    } catch (e) {
      // 不是JSON格式，直接处理为纯文本
      // 先检查是否包含有意义的内容（非控制字符）
      const filteredText = processedBlock
        .replace(/\[DONE\]/g, '')
        .replace(/\{\}/g, '')
        .replace(/[\[\]{}]/g, ' ')
        .replace(/\s+/g, ' ')
        .trim();
      
      if (filteredText) {
        result += filteredText + ' ';
      }
    }
  }
  
  // 最终清理：确保没有残留的控制字符和格式信息
  result = result
    .replace(/data:/g, '')  // 再次移除data:前缀，确保彻底清理
    .replace(/[\[\]{}]/g, ' ')
    .replace(/\s+/g, ' ')
    .replace(/^\s+|\s+$/g, '')
    .replace(/\[DONE\]/g, '')
    .replace(/\{\}/g, '');
  
  // 确保不返回空字符串
  if (!result.trim() && cleanedText.trim()) {
    // 如果提取失败但原始文本存在，使用更简单的清理方法
    return cleanedText
      .replace(/data:/g, '')
      .replace(/[\[\]{}]/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();
  }
  
  return result;
};

/**
 * 处理流式响应块
 * @param {string} chunk - 要处理的数据块
 */
const processStreamChunk = (chunk) => {
  setIsLoading(true);
  if (!chunk) return;

  try {
    // 记录原始数据的特征，帮助调试
    if (typeof chunk === 'string') {
      console.debug(`接收流数据: 长度=${chunk.length}, 包含data:前缀=${chunk.includes('data:')} ${chunk.length > 100 ? '(数据过大仅记录特征)' : `数据开头: ${chunk.substring(0, 30)}...`}`);
    } else {
      console.debug(`接收到非字符串类型的数据: ${typeof chunk}`);
    }
    
    // 使用增强的清理函数彻底处理响应
    const cleanedContent = parseSSEChunk(chunk);
    
    if (cleanedContent) {
      console.debug(`清理后的内容: ${cleanedContent.length > 30 ? cleanedContent.substring(0, 30) + '...' : cleanedContent}`);
      
      // 更新内容并滚动到底部
      setContent((prevContent) => {
        const newContent = prevContent + cleanedContent;
        // 使用防抖动函数延迟滚动，避免频繁滚动
        debouncedScrollToBottom();
        return newContent;
      });
    } else {
      console.warn('清理后的内容为空，可能存在解析问题');
    }
  } catch (error) {
    console.error('处理流式响应时出错:', error, '原始数据:', chunk?.substring?.(0, 100));
    
    // 尝试使用备用方法处理
    try {
      if (typeof chunk === 'string') {
        // 仅应用最基本的清理，保留可能有用的内容
        const backupCleanedContent = chunk
          .replace(/data:/g, '')
          .replace(/[\[\]{}]/g, ' ')
          .replace(/\s+/g, ' ')
          .trim();
          
        if (backupCleanedContent) {
          console.warn('使用备用清理方法处理数据');
          setContent((prevContent) => prevContent + backupCleanedContent);
        }
      }
    } catch (backupError) {
      console.error('备用清理方法也失败:', backupError);
    }
  }
};

// 使用防抖动函数避免频繁滚动
const debouncedScrollToBottom = useCallback(
  debounce(() => {
    if (containerRef.current) {
      containerRef.current.scrollIntoView({
        behavior: 'smooth',
        block: 'end',
      });
    }
  }, 100),
  []
);

// 处理流式响应开始
const handleStreamingStart = useCallback(() => {
  // 重置状态
  setContent('');
  setIsLoading(true);
  
  // 滚动到底部确保用户能看到新内容
  setTimeout(() => {
    if (containerRef.current) {
      containerRef.current.scrollIntoView({
        behavior: 'smooth',
        block: 'end',
      });
    }
  }, 100);
}, []); 