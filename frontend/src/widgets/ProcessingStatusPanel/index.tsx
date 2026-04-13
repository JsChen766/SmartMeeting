import React from 'react';
import {MeetingStatus} from '../../shared/types';

export interface ProcessingStatusPanelProps {
    status: MeetingStatus;
    timedOut?: boolean;
}

const STATUS_LABELS: Record<MeetingStatus, string> = {
    uploaded: 'Uploaded',
    processing: 'Processing',
    completed: 'Completed',
    failed: 'Failed',
};

export const ProcessingStatusPanel: React.FC<ProcessingStatusPanelProps> = ({status, timedOut = false}) => {
    return (
        <div className="rounded-lg border border-white/10 bg-white/5 p-3 text-xs font-mono text-white/70">
            <div>Status: {STATUS_LABELS[status]}</div>
            {timedOut ? <div className="text-yellow-400 mt-1">Auto polling timeout reached.</div> : null}
        </div>
    );
};

