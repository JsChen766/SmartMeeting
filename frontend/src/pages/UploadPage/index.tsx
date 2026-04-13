import React, {useMemo, useRef, useState} from 'react';
import {useNavigate} from 'react-router-dom';
import {useUploadMeetingMutation} from '../../features/upload-meeting';
import {useStartMeetingProcessMutation} from '../../features/start-processing';
import {normalizeApiError} from '../../shared/api';
import {LanguageCode} from '../../shared/types';
import {mapLanguageCodeToName} from '../../shared/utils/language';
import {ErrorBanner} from '../../widgets/ErrorBanner';

export const UploadPage: React.FC = () => {
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [targetLanguage, setTargetLanguage] = useState<LanguageCode>('man');
    const [isUploading, setIsUploading] = useState(false);
    const [uploadProgress, setUploadProgress] = useState(0);
    const [isDragActive, setIsDragActive] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const inputRef = useRef<HTMLInputElement | null>(null);
    const navigate = useNavigate();
    const uploadMeetingMutation = useUploadMeetingMutation();
    const startMeetingProcessMutation = useStartMeetingProcessMutation();

    const languageOptions = useMemo((): Array<{ code: LanguageCode; name: string }> => {
        return [
            {code: 'man', name: mapLanguageCodeToName('man')},
            {code: 'can', name: mapLanguageCodeToName('can')},
            {code: 'eng', name: mapLanguageCodeToName('eng')},
        ];
    }, []);

    const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        const files = event.target.files;
        if (files && files.length > 0) {
            const file = files[0];
            if (!file.type.startsWith('audio/') && !file.name.endsWith('.mp3')) {
                setError('僅支援音頻檔案（如 MP3）。');
                return;
            }
            setSelectedFile(file);
            setError(null);
        }
    };

    const handleDrag = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === 'dragenter' || e.type === 'dragover') {
            setIsDragActive(true);
        } else if (e.type === 'dragleave') {
            setIsDragActive(false);
        }
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragActive(false);
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            const file = e.dataTransfer.files[0];
            if (!file.type.startsWith('audio/') && !file.name.endsWith('.mp3')) {
                setError('僅支援音頻檔案（如 MP3）。');
                return;
            }
            setSelectedFile(file);
            setError(null);
        }
    };

    const handleUpload = async () => {
        if (!selectedFile) return;

        setIsUploading(true);
        setUploadProgress(0);
        setError(null);

        const interval = setInterval(() => {
            setUploadProgress((prev) => {
                if (prev >= 90) {
                    return 90;
                }
                return prev + 5;
            });
        }, 100);

        try {
            const uploadedMeeting = await uploadMeetingMutation.mutateAsync({
                file: selectedFile,
                langHint: targetLanguage,
                fileName: selectedFile.name,
            });

            const processingMeeting = await startMeetingProcessMutation.mutateAsync({
                meetingId: uploadedMeeting.meeting_id,
                targetLang: targetLanguage,
                enableSummary: true,
                enableTranslation: false,
            });

            setUploadProgress(100);
            navigate(
                `/meetings/${processingMeeting.meeting_id}?fileName=${encodeURIComponent(selectedFile.name)}&targetLang=${targetLanguage}`,
            );
        } catch (caughtError) {
            const apiError = normalizeApiError(caughtError);
            setError(`ERROR [${apiError.code}]: ${apiError.message}`);
        } finally {
            clearInterval(interval);
            setIsUploading(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center p-6 relative overflow-hidden">
            {/* 裝飾背景元素 */}
            <div
                className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-cyan-500/10 rounded-full blur-[120px] animate-pulse"/>
            <div
                className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-magenta-500/10 rounded-full blur-[120px] animate-pulse"
                style={{backgroundColor: 'rgba(255, 0, 255, 0.1)'}}/>

            <div className="tech-card w-full max-w-2xl p-8 sm:p-12 relative">
                <div
                    className="absolute top-4 right-4 text-[10px] font-mono text-cyan-500/50 uppercase tracking-widest">
                    System v2.0 // Ready
                </div>

                <header className="text-center mb-10">
                    <h1 className="text-4xl font-black tracking-tighter neon-glow-cyan mb-2 uppercase italic">
                        Smart Meeting <span className="text-white">Assistant</span>
                    </h1>
                    <p className="text-cyan-400/60 font-mono text-sm uppercase tracking-widest animate-flicker">
                        Digitalizing your conversations
                    </p>
                </header>

                <div className="space-y-8">
                    {/* 檔案上傳區 */}
                    <div
                        onDragEnter={handleDrag}
                        onDragLeave={handleDrag}
                        onDragOver={handleDrag}
                        onDrop={handleDrop}
                        onClick={() => inputRef.current?.click()}
                        className={`group relative border-2 border-dashed transition-all duration-500 rounded-xl p-10 text-center cursor-pointer overflow-hidden ${
                            isDragActive
                                ? 'border-cyan-400 bg-cyan-500/10'
                                : 'border-cyan-500/20 hover:border-cyan-500/40 hover:bg-white/5'
                        }`}
                    >
                        <input
                            ref={inputRef}
                            type="file"
                            className="hidden"
                            accept="audio/*"
                            onChange={handleFileChange}
                        />

                        <div className="relative z-10">
                            <div
                                className="mb-4 inline-flex items-center justify-center w-16 h-16 rounded-full bg-cyan-500/10 border border-cyan-500/30 group-hover:scale-110 transition-transform duration-300">
                                <svg className="w-8 h-8 text-cyan-400" fill="none" stroke="currentColor"
                                     viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5"
                                          d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/>
                                </svg>
                            </div>

                            {selectedFile ? (
                                <div className="space-y-2">
                                    <p className="text-xl font-bold text-white tracking-tight">{selectedFile.name}</p>
                                    <p className="text-cyan-400/60 font-mono text-xs uppercase">
                                        {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB // READY TO PROCESS
                                    </p>
                                </div>
                            ) : (
                                <div className="space-y-2">
                                    <p className="text-xl font-bold text-cyan-100 uppercase tracking-tight">Drop Audio
                                        File</p>
                                    <p className="text-cyan-400/40 font-mono text-xs uppercase tracking-widest">
                                        Support: MP3, WAV, M4A // Max 500MB
                                    </p>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* 語言選擇 */}
                    <div className="space-y-4">
                        <label className="block text-xs font-mono text-cyan-400/60 uppercase tracking-[0.2em] ml-1">
                            Select Target Language
                        </label>
                        <div className="grid grid-cols-3 gap-4">
                            {languageOptions.map((lang) => (
                                <button
                                    key={lang.code}
                                    onClick={() => setTargetLanguage(lang.code)}
                                    className={`py-3 px-4 rounded-lg font-bold transition-all duration-300 border uppercase tracking-wider text-xs ${
                                        targetLanguage === lang.code
                                            ? 'bg-cyan-500 border-cyan-400 text-black shadow-[0_0_20px_rgba(0,243,255,0.4)]'
                                            : 'bg-white/5 border-white/10 text-white/60 hover:border-cyan-500/40 hover:text-cyan-400'
                                    }`}
                                >
                                    {lang.name}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* 錯誤提示 */}
                    {error && <ErrorBanner message={error}/>}

                    {/* 上傳進度 */}
                    {isUploading && (
                        <div className="space-y-2">
                            <div
                                className="flex justify-between text-[10px] font-mono text-cyan-400/60 uppercase tracking-widest">
                                <span>Processing Stream...</span>
                                <span>{uploadProgress}%</span>
                            </div>
                            <div className="h-1 w-full bg-white/5 rounded-full overflow-hidden">
                                <div
                                    className="h-full bg-cyan-500 transition-all duration-300 shadow-[0_0_10px_#00f3ff]"
                                    style={{width: `${uploadProgress}%`}}
                                />
                            </div>
                        </div>
                    )}

                    {/* 提交按鈕 */}
                    <button
                        onClick={handleUpload}
                        disabled={!selectedFile || isUploading}
                        className="tech-button w-full h-14"
                    >
                        {isUploading ? 'Initializing...' : 'Execute Process'}
                    </button>
                </div>
            </div>

            {/* 底部裝飾 */}
            <div
                className="absolute bottom-6 left-1/2 -translate-x-1/2 font-mono text-[10px] text-white/20 uppercase tracking-[0.5em]">
                End-to-End Encryption // Secure Mode
            </div>
        </div>
    );
};
