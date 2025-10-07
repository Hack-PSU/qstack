// PostHog TypeScript definitions

declare global {
  interface Window {
    posthog?: {
      init: (apiKey: string, config: PostHogConfig) => void;
      identify: (distinctId: string, properties?: Record<string, any>) => void;
      capture: (eventName: string, properties?: Record<string, any>) => void;
      reset: () => void;
      isFeatureEnabled: (flag: string) => boolean;
      getFeatureFlag: (flag: string) => string | boolean | undefined;
      onFeatureFlags: (callback: () => void) => void;
      startSessionRecording: () => void;
      stopSessionRecording: () => void;
    };
  }

  interface ImportMetaEnv {
    readonly VITE_POSTHOG_KEY?: string;
    readonly VITE_POSTHOG_HOST?: string;
  }

  interface ImportMeta {
    readonly env: ImportMetaEnv;
  }
}

interface PostHogConfig {
  api_host?: string;
  person_profiles?: 'always' | 'identified_only' | 'never';
  capture_pageview?: boolean;
  capture_pageleave?: boolean;
  autocapture?: boolean;
  disable_session_recording?: boolean;
  enable_recording_console_log?: boolean;
  session_recording?: {
    maskAllInputs?: boolean;
    maskInputFn?: (text: string, element?: HTMLElement) => string;
  };
}

export {};
