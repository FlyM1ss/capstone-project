import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { UserProfile } from '@/types';
import { getUserProfile } from '@/api/account';

const UserContext = createContext<UserProfile | null>(null);

export function UserProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);

  useEffect(() => {
    getUserProfile().then(setUser);
  }, []);

  return <UserContext.Provider value={user}>{children}</UserContext.Provider>;
}

export function useUser(): UserProfile | null {
  return useContext(UserContext);
}
