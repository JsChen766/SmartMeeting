import {QueryClient, QueryClientProvider} from '@tanstack/react-query';
import React from 'react';

const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            staleTime: 1000,
            refetchOnWindowFocus: false,
            retry: 1,
        },
    },
});

export const AppProviders: React.FC<React.PropsWithChildren> = ({children}) => {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
};

