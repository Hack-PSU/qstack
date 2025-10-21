import { create } from "zustand";
import * as auth from "../api/auth";

// PostHog types
declare global {
  interface Window {
    posthog?: {
      identify: (distinctId: string, properties?: Record<string, unknown>) => void;
      reset: () => void;
    };
  }
}

interface userState {
  name: string;
  email: string;
  role: string;
  loggedIn: boolean | undefined;
  location: string;
  zoomlink: string;
  discord: string;
  phone: string;
  preferred: string;
  discordRequired?: boolean;
  contactRequired?: boolean;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  getUser: () => Promise<any>;
}

export const useUserStore = create<userState>((set) => ({
  name: "",
  email: "",
  role: "",
  location: "",
  zoomlink: "",
  discord: "",
  phone: "",
  preferred: "",
  loggedIn: undefined,
  discordRequired: false,
  contactRequired: false,
  getUser: async () => {
    const userData = await auth.whoami();
    set(userData);

    // Identify user in PostHog if logged in
    if (userData.loggedIn && userData.id && window.posthog) {
      window.posthog.identify(userData.id, {
        email: userData.email || undefined,
        name: userData.name || undefined,
        role: userData.role || undefined,
      });
    } else if (!userData.loggedIn && window.posthog) {
      // Reset PostHog identity on logout
      window.posthog.reset();
    }


    // Redirect to contact info connect page if required
    if ((userData.discordRequired || userData.contactRequired) && window.location.pathname !== "/connect-discord") {
      window.location.replace("/connect-discord");
    }

    return userData;
  },
}));
