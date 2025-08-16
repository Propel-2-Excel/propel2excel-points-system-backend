/*
 * THIS FILE IS FOR YOUR NEXT.JS FRONTEND PROJECT
 * 
 * Copy this entire file to: P2E-Dashboard/src/services/api.ts
 * 
 * Then install @types/node in your frontend:
 * npm install --save-dev @types/node
 */

// Use Render URL in production, localhost for development
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api';

interface ApiResponse<T> {
  data?: T;
  error?: string;
  status: number;
}

class ApiService {
  private baseURL: string;
  private token: string | null = null;

  constructor() {
    this.baseURL = API_BASE_URL;
    // Get token from localStorage on client side
    if (typeof window !== 'undefined') {
      this.token = localStorage.getItem('access_token');
    }
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<ApiResponse<T>> {
    const url = `${this.baseURL}${endpoint}`;
    
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...options.headers as Record<string, string>,
    };

    if (this.token) {
      headers.Authorization = `Bearer ${this.token}`;
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers,
        credentials: 'include', // Include cookies for CORS
      });

      const data = await response.json();

      if (!response.ok) {
        return {
          error: data.error || `API Error: ${response.status} ${response.statusText}`,
          status: response.status,
        };
      }

      return {
        data,
        status: response.status,
      };
    } catch (error) {
      return {
        error: error instanceof Error ? error.message : 'Network error',
        status: 0,
      };
    }
  }

  // Authentication Methods
  async register(userData: {
    username: string;
    email: string;
    password: string;
    role?: string;
    company?: string;
    university?: string;
  }): Promise<ApiResponse<{ user: any; tokens: { access: string; refresh: string } }>> {
    return this.request('/users/register/', {
      method: 'POST',
      body: JSON.stringify(userData),
    });
  }

  async login(credentials: { username: string; password: string }): Promise<ApiResponse<{
    user: any;
    tokens: { access: string; refresh: string };
  }>> {
    const response = await this.request<{
      user: any;
      tokens: { access: string; refresh: string };
    }>('/users/login/', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });

    // Store tokens on successful login
    if (response.data && typeof window !== 'undefined') {
      localStorage.setItem('access_token', response.data.tokens.access);
      localStorage.setItem('refresh_token', response.data.tokens.refresh);
      this.token = response.data.tokens.access;
    }

    return response;
  }

  async getProfile(): Promise<ApiResponse<any>> {
    return this.request('/users/profile/');
  }

  // Points System Methods
  async getActivities(): Promise<ApiResponse<any[]>> {
    return this.request('/activities/');
  }

  async getPointsHistory(): Promise<ApiResponse<any[]>> {
    return this.request('/points-logs/');
  }

  async addPoints(userId: number, data: { 
    activity_type: string; 
    details?: string 
  }): Promise<ApiResponse<any>> {
    return this.request(`/users/${userId}/add_points/`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Incentives Methods
  async getIncentives(): Promise<ApiResponse<any[]>> {
    return this.request('/incentives/');
  }

  async redeemIncentive(incentiveId: number): Promise<ApiResponse<any>> {
    return this.request('/redemptions/redeem/', {
      method: 'POST',
      body: JSON.stringify({ incentive_id: incentiveId }),
    });
  }

  async getRedemptions(): Promise<ApiResponse<any[]>> {
    return this.request('/redemptions/');
  }

  // Admin Methods (admin role required)
  async approveRedemption(redemptionId: number): Promise<ApiResponse<any>> {
    return this.request(`/redemptions/${redemptionId}/approve/`, {
      method: 'POST',
    });
  }

  async rejectRedemption(redemptionId: number, notes?: string): Promise<ApiResponse<any>> {
    return this.request(`/redemptions/${redemptionId}/reject/`, {
      method: 'POST',
      body: JSON.stringify({ admin_notes: notes }),
    });
  }

  // Discord Integration Methods
  async startDiscordLink(): Promise<ApiResponse<{ code: string }>> {
    return this.request('/link/start', { method: 'POST' });
  }

  async checkLinkStatus(): Promise<ApiResponse<{ linked: boolean; discord_id?: string }>> {
    return this.request('/link/status');
  }

  // Auth Utility Methods
  logout(): void {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      this.token = null;
    }
  }

  isAuthenticated(): boolean {
    return !!this.token;
  }

  getToken(): string | null {
    return this.token;
  }

  // Refresh token method
  async refreshToken(): Promise<boolean> {
    if (typeof window === 'undefined') return false;
    
    const refreshToken = localStorage.getItem('refresh_token');
    if (!refreshToken) return false;

    try {
      const response = await fetch(`${this.baseURL}/token/refresh/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh: refreshToken }),
      });

      if (response.ok) {
        const data = await response.json();
        localStorage.setItem('access_token', data.access);
        this.token = data.access;
        return true;
      }
    } catch (error) {
      console.error('Token refresh failed:', error);
    }

    // If refresh fails, clear tokens
    this.logout();
    return false;
  }
}

export const apiService = new ApiService();

// TypeScript interfaces for your components
export interface User {
  id: number;
  username: string;
  email: string;
  first_name?: string;
  last_name?: string;
  role: 'admin' | 'student' | 'company' | 'university';
  company?: string;
  university?: string;
  discord_id?: string;
  total_points: number;
  created_at: string;
  updated_at: string;
}

export interface Activity {
  id: number;
  name: string;
  activity_type: 'resume_upload' | 'event_attendance' | 'resource_share' | 'like_interaction' | 'linkedin_post' | 'discord_activity';
  points_value: number;
  description: string;
  is_active: boolean;
  created_at: string;
}

export interface PointsLog {
  id: number;
  user: number;
  activity: Activity;
  points_earned: number;
  details: string;
  timestamp: string;
}

export interface Incentive {
  id: number;
  name: string;
  description: string;
  points_required: number;
  sponsor: string;
  status: 'available' | 'unlocked' | 'redeemed';
  is_active: boolean;
  is_unlocked?: boolean; // Added by backend serializer
  created_at: string;
}

export interface Redemption {
  id: number;
  user: number;
  incentive: Incentive;
  points_spent: number;
  status: 'pending' | 'approved' | 'rejected';
  admin_notes: string;
  redeemed_at: string;
  processed_at?: string;
}

export interface UserStatus {
  user: number;
  warnings: number;
  points_suspended: boolean;
  suspension_end?: string;
  last_activity: string;
}

export interface DiscordLinkResponse {
  code: string;
  expires_in_minutes: number;
}

export interface LinkStatusResponse {
  linked: boolean;
  discord_id?: string;
}
