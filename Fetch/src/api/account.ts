import { UserProfile } from '@/types';
import { apiGet } from './client';
import { mockUser } from '@/data/mockData';

export async function getUserProfile(): Promise<UserProfile> {
  return apiGet<UserProfile>('/account/profile', mockUser);
}
