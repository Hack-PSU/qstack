import { create } from "zustand";
import * as auth from "../api/auth";

interface userState {
  name: string;
  email: string;
  role: string;
  loggedIn: boolean | undefined;
  location: string;
  zoomlink: string;
  discord: string;
  discordRequired?: boolean;
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
  loggedIn: undefined,
  discordRequired: false,
  getUser: async () => {
    const userData = await auth.whoami();
    set(userData);

    // Redirect to Discord connect page if required
    if (userData.discordRequired && window.location.pathname !== "/connect-discord") {
      window.location.replace("/connect-discord");
    }

    return userData;
  },
}));
