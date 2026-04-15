import {useMutation} from '@tanstack/react-query';
import {startMeetingProcess} from '../../../shared/api';
import {LanguageCode} from '../../../shared/types';

export interface StartMeetingProcessInput {
    meetingId: string;
    targetLang?: LanguageCode;
    enableTranslation?: boolean;
    translationTargetLang?: LanguageCode;
    enableSummary?: boolean;
}

export const useStartMeetingProcessMutation = () => {
    return useMutation({
        mutationFn: ({
                         meetingId,
                         targetLang,
                         enableTranslation = false,
                         translationTargetLang,
                         enableSummary = true,
                     }: StartMeetingProcessInput) => {
            return startMeetingProcess({
                meeting_id: meetingId,
                target_lang: targetLang,
                enable_translation: enableTranslation,
                translation_target_lang: translationTargetLang,
                enable_summary: enableSummary,
            });
        },
    });
};

