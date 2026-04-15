import React from 'react';

export interface ErrorBannerProps {
    message: string;
}

export const ErrorBanner: React.FC<ErrorBannerProps> = ({message}) => {
    return (
        <div
            className="p-4 bg-red-500/10 border border-red-500/50 rounded-lg text-red-400 text-sm font-mono flex items-center gap-3">
            <svg className="w-5 h-5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
                <path
                    fillRule="evenodd"
                    d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
                    clipRule="evenodd"
                />
            </svg>
            <span>{message}</span>
        </div>
    );
};

