import { UserProfile } from '@/types';

export function getInitials(user: UserProfile | null): string {
  if (!user) return '?';
  return user.firstName[0] + (user.name.split(' ')[1]?.[0] ?? '');
}
