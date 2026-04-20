import { createContext, useContext, ReactNode } from 'react';
import { UserProfile } from '@/types';
import { getDemoUser } from '@/api/account';

const UserContext = createContext<UserProfile | null>(null);

export function UserProvider({ children }: { children: ReactNode }) {
  // TODO: replace with real auth flow (login -> JWT -> GET /api/auth/me)
  const user = getDemoUser();

  return <UserContext.Provider value={user}>{children}</UserContext.Provider>;
}

export function useUser(): UserProfile | null {
  return useContext(UserContext);
}
