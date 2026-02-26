import { useMemo } from 'react';
import { useAuthStore } from '@/stores/authStore';

export function usePermission(permission: string) {
  const user = useAuthStore((s) => s.user);

  return useMemo(() => {
    if (!user) return false;
    if (user.role === 'admin') return true;
    const permissions = (user as any).permissions ?? [];
    return permissions.includes(permission);
  }, [permission, user]);
}
