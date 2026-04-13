import {useMutation} from '@tanstack/react-query';
import {uploadMeeting} from '../../../shared/api';
import {LanguageCode} from '../../../shared/types';

export interface UploadMeetingInput {
    file: File;
    langHint?: LanguageCode;
    fileName?: string;
}

export const useUploadMeetingMutation = () => {
    return useMutation({
        mutationFn: ({file, langHint, fileName}: UploadMeetingInput) => {
            return uploadMeeting({
                file,
                langHint,
                fileName,
            });
        },
    });
};

