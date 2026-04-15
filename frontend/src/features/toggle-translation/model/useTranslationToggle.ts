import { useState } from 'react';

export const useTranslationToggle = (initialState: boolean = true) => {
  const [showTranslation, setShowTranslation] = useState(initialState);

  const toggleTranslation = () => setShowTranslation((prev) => !prev);

  return { showTranslation, toggleTranslation };
};
