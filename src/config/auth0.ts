export const auth0Config = {
    domain: import.meta.env.VITE_AUTH0_DOMAIN,
    clientId: import.meta.env.VITE_AUTH0_CLIENT_ID,
    cacheLocation: 'localstorage' as const,
    useRefreshTokens: true,
    authorizationParams: {
        redirect_uri: window.location.origin + import.meta.env.BASE_URL,
        scope: 'openid profile email',
    },
};
