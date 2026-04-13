import { UserProfile } from '@/types';

// Demo user for prototype (no auth wired up yet).
// When auth is implemented, this will call GET /api/auth/me with a JWT token.
const DEMO_USER: UserProfile = {
  id: 'demo-admin',
  name: 'Admin User',
  firstName: 'Admin',
  email: 'admin@deloitte.com',
  department: 'Technology',
  title: 'Administrator',
};

export function getDemoUser(): UserProfile {
  return DEMO_USER;
}
