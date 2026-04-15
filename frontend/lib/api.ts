import axios, { type AxiosRequestConfig, type AxiosError } from "axios";

const baseURL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL,
  timeout: 15000,
  withCredentials: false,
  headers: {
    "Content-Type": "application/json"
  }
});

const ACCESS_TOKEN_KEY = "access_token";
const REFRESH_TOKEN_KEY = "refresh_token";
let onAuthFailure: (() => void) | null = null;

const refreshClient = axios.create({
  baseURL,
  timeout: 15000,
  withCredentials: false,
  headers: {
    "Content-Type": "application/json"
  }
});

export function setAuthToken(token: string | null) {
  if (token) {
    api.defaults.headers.common.Authorization = `Bearer ${token}`;
  } else {
    delete api.defaults.headers.common.Authorization;
  }
}

export function setAuthFailureHandler(handler: (() => void) | null) {
  onAuthFailure = handler;
}

export function setAuthTokens(accessToken: string | null, refreshToken?: string | null) {
  if (typeof window === "undefined") {
    setAuthToken(accessToken);
    return;
  }
  if (accessToken) {
    sessionStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  } else {
    sessionStorage.removeItem(ACCESS_TOKEN_KEY);
  }
  if (refreshToken !== undefined) {
    if (refreshToken) {
      sessionStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
    } else {
      sessionStorage.removeItem(REFRESH_TOKEN_KEY);
    }
  }
  setAuthToken(accessToken);
}

export function clearAuthTokens() {
  if (typeof window !== "undefined") {
    sessionStorage.removeItem(ACCESS_TOKEN_KEY);
    sessionStorage.removeItem(REFRESH_TOKEN_KEY);
  }
  setAuthToken(null);
}

function getStoredTokens() {
  if (typeof window === "undefined") {
    return { accessToken: null, refreshToken: null };
  }
  return {
    accessToken: sessionStorage.getItem(ACCESS_TOKEN_KEY),
    refreshToken: sessionStorage.getItem(REFRESH_TOKEN_KEY)
  };
}

api.interceptors.request.use((config) => {
  const { accessToken } = getStoredTokens();
  const headers = axios.AxiosHeaders.from(config.headers);
  if (accessToken && !headers.get("Authorization")) {
    headers.set("Authorization", `Bearer ${accessToken}`);
    config.headers = headers;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as (AxiosRequestConfig & { _retry?: boolean }) | undefined;
    if (!originalRequest) {
      return Promise.reject(error);
    }

    const status = error.response?.status;
    if (status !== 401 || originalRequest._retry) {
      return Promise.reject(error);
    }

    const { refreshToken } = getStoredTokens();
    if (!refreshToken) {
      clearAuthTokens();
      onAuthFailure?.();
      return Promise.reject(error);
    }

    originalRequest._retry = true;
    try {
      const refreshResponse = await refreshClient.post<{ access_token: string; refresh_token: string }>(
        "/auth/refresh",
        { refresh_token: refreshToken }
      );
      const newAccess = refreshResponse.data.access_token;
      const newRefresh = refreshResponse.data.refresh_token;
      setAuthTokens(newAccess, newRefresh);

      const retryHeaders = axios.AxiosHeaders.from((originalRequest.headers ?? {}) as any);
      retryHeaders.set("Authorization", `Bearer ${newAccess}`);
      originalRequest.headers = retryHeaders;
      return api.request(originalRequest);
    } catch (refreshError) {
      clearAuthTokens();
      onAuthFailure?.();
      return Promise.reject(refreshError);
    }
  }
);

export async function fetcher<T = unknown>(
  url: string,
  config?: AxiosRequestConfig
): Promise<T> {
  const response = await api.get<T>(url, config);
  return response.data;
}

export async function uploadDocument(
  file: File,
  onProgress?: (percent: number) => void
): Promise<void> {
  const formData = new FormData();
  formData.append("file", file);

  await api.post("/documents/upload", formData, {
    headers: {
      "Content-Type": "multipart/form-data"
    },
    onUploadProgress: (event) => {
      if (!event.total) return;
      const percent = Math.round((event.loaded / event.total) * 100);
      onProgress?.(percent);
    }
  });
}

