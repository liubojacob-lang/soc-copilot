"use client";

import { useState, useEffect } from "react";

interface User {
  id: number;
  username: string;
  email: string;
  role: string;
  is_active: boolean;
  last_login_at: string | null;
  created_at: string;
}

export function useUsers() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchUsers = async () => {
    setLoading(true);
    setError(null);

    try {
      const token = localStorage.getItem("access_token");
      const response = await fetch("/api/users", {
        headers: {
          "Authorization": \`Bearer \${token}\`
        }
      });

      if (!response.ok) {
        throw new Error("Failed to fetch users");
      }

      const data = await response.json();
      setUsers(data || []);
    } catch (err: any) {
      setError(err.message);
      // For demo/testing, provide mock data
      setUsers([
        {
          id: 1,
          username: "admin",
          email: "admin@example.com",
          role: "admin",
          is_active: true,
          last_login_at: new Date().toISOString(),
          created_at: new Date().toISOString()
        },
        {
          id: 2,
          username: "analyst1",
          email: "analyst1@example.com",
          role: "analyst",
          is_active: true,
          last_login_at: new Date(Date.now() - 86400000).toISOString(),
          created_at: new Date().toISOString()
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const deleteUser = async (userId: number) => {
    try {
      const token = localStorage.getItem("access_token");
      const response = await fetch(\`/api/users/\${userId}\`, {
        method: "DELETE",
        headers: {
          "Authorization": \`Bearer \${token}\`
        }
      });

      if (!response.ok) {
        throw new Error("Failed to delete user");
      }

      // Update local state
      setUsers(users.filter(u => u.id !== userId));
    } catch (err: any) {
      setError(err.message);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  return {
    users,
    loading,
    error,
    fetchUsers,
    deleteUser
  };
}

export function generatePassword(): string {
  const length = 12;
  const charset = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*";
  let retVal = "";
  for (let i = 0, n = charset.length; i < length; ++i) {
    retVal += charset.charAt(Math.floor(Math.random() * n));
  }
  return retVal;
}
