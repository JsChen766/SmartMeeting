export const mapLanguageCodeToName = (code: string): string => {
  const normalizedCode = code.toLowerCase();
  switch (normalizedCode) {
    case 'man':
    case 'zh':
      return '普通話';
    case 'can':
    case 'yue':
      return '粵語';
    case 'eng':
    case 'en':
      return '英文';
    default:
      return code || '未知語言';
  }
};
