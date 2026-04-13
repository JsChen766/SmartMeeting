import { useState, useMemo } from 'react';
import { TranscriptSegment } from '../../../shared/types';

export const useTranscriptSearch = (segments: TranscriptSegment[]) => {
  const [searchQuery, setSearchQuery] = useState('');

  const filteredSegments = useMemo(() => {
    if (!searchQuery.trim()) {
      return segments;
    }

    const lowerQuery = searchQuery.toLowerCase();
    return segments.filter((segment) => {
      const textMatch = segment.text.toLowerCase().includes(lowerQuery);
      const speakerMatch = (segment.speaker || 'UNKNOWN').toLowerCase().includes(lowerQuery);
      const translationMatch = segment.translation?.toLowerCase().includes(lowerQuery);

      return textMatch || speakerMatch || translationMatch;
    });
  }, [segments, searchQuery]);

  return {
    searchQuery,
    setSearchQuery,
    filteredSegments,
  };
};
