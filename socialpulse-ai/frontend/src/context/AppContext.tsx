import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react"
import { api, getStoredToken, setStoredToken } from "../services/api"
import type {
  AnalyticsFilterParams,
  DatasetRecord,
  NotificationItem,
  UserProfile,
} from "../types/api"

export type ThemeMode = "dark" | "light"

export interface ToastItem {
  id: string
  title: string
  message?: string
  variant: "success" | "error" | "info" | "warning"
}

export interface ConfirmState {
  title: string
  message: string
  confirmLabel?: string
  danger?: boolean
  onConfirm: () => Promise<void> | void
}

interface AppContextValue {
  theme: ThemeMode
  toggleTheme: () => void
  setThemeMode: (mode: ThemeMode) => void

  user: UserProfile | null
  authLoading: boolean
  login: (email: string, password: string) => Promise<UserProfile>
  register: (payload: {
    email: string
    password: string
    full_name: string
    role?: string
    organization?: string
  }) => Promise<UserProfile>
  logout: () => Promise<void>
  updateProfile: (payload: {
    full_name: string
    role: string
    organization: string
    bio: string
  }) => Promise<UserProfile>
  changePassword: (currentPassword: string, newPassword: string) => Promise<void>

  datasets: DatasetRecord[]
  activeDataset: DatasetRecord | null
  datasetVersion: number
  refreshDatasets: () => Promise<void>
  activateDatasetById: (id: number) => Promise<void>
  bumpDatasetVersion: () => void

  globalFilters: AnalyticsFilterParams
  setGlobalFilters: (
    updater:
      | AnalyticsFilterParams
      | ((prev: AnalyticsFilterParams) => AnalyticsFilterParams)
  ) => void
  resetFilters: () => void

  notifications: NotificationItem[]
  unreadCount: number
  refreshNotifications: () => Promise<void>
  markRead: (id: number) => Promise<void>
  markAllRead: () => Promise<void>

  toasts: ToastItem[]
  pushToast: (toast: Omit<ToastItem, "id">) => void
  dismissToast: (id: string) => void

  selectedPostId: string | null
  openPostDetail: (postId: string) => void
  closePostDetail: () => void

  confirmState: ConfirmState | null
  requestConfirm: (state: ConfirmState) => void
  closeConfirm: () => void
}

const AppContext = createContext<AppContextValue | null>(null)

const THEME_KEY = "socialpulse_theme"

function getInitialTheme(): ThemeMode {
  try {
    const saved = localStorage.getItem(THEME_KEY)
    if (saved === "light" || saved === "dark") return saved
  } catch {
    // ignore
  }
  return "dark"
}

export function AppProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<ThemeMode>(getInitialTheme)
  const [user, setUser] = useState<UserProfile | null>(null)
  const [authLoading, setAuthLoading] = useState(true)

  const [datasets, setDatasets] = useState<DatasetRecord[]>([])
  const [activeDataset, setActiveDataset] = useState<DatasetRecord | null>(null)
  const [datasetVersion, setDatasetVersion] = useState(0)

  const [globalFilters, setGlobalFiltersState] = useState<AnalyticsFilterParams>({
    platform: "",
    sentiment: "",
    start_date: "",
    end_date: "",
    search: "",
  })

  const [notifications, setNotifications] = useState<NotificationItem[]>([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [toasts, setToasts] = useState<ToastItem[]>([])
  const [selectedPostId, setSelectedPostId] = useState<string | null>(null)
  const [confirmState, setConfirmState] = useState<ConfirmState | null>(null)

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme)
    try {
      localStorage.setItem(THEME_KEY, theme)
    } catch {
      // ignore
    }
  }, [theme])

  const pushToast = useCallback((toast: Omit<ToastItem, "id">) => {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
    setToasts((prev) => [...prev, { ...toast, id }])
    window.setTimeout(() => {
      setToasts((prev) => prev.filter((item) => item.id !== id))
    }, 4500)
  }, [])

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((item) => item.id !== id))
  }, [])

  const refreshNotifications = useCallback(async () => {
    try {
      const res = await api.notifications()
      setNotifications(res.notifications)
      setUnreadCount(res.unread_count)
    } catch {
      // backend might be starting up
    }
  }, [])

  const refreshDatasets = useCallback(async () => {
    try {
      const [listRes, activeRes] = await Promise.all([
        api.datasets(),
        api.activeDataset(),
      ])
      setDatasets(listRes.datasets)
      setActiveDataset(activeRes.dataset)
    } catch {
      // ignore initial offline error; views display clean error state
    }
  }, [])

  useEffect(() => {
    let mounted = true
    async function bootstrap() {
      const token = getStoredToken()
      if (token) {
        try {
          const res = await api.me()
          if (mounted) setUser(res.user)
        } catch {
          setStoredToken(null)
          if (mounted) setUser(null)
        }
      }
      if (mounted) setAuthLoading(false)
      await Promise.all([refreshDatasets(), refreshNotifications()])
    }
    bootstrap()
    return () => {
      mounted = false
    }
  }, [refreshDatasets, refreshNotifications])

  const toggleTheme = useCallback(() => {
    setTheme((prev) => (prev === "dark" ? "light" : "dark"))
  }, [])

  const setThemeMode = useCallback((mode: ThemeMode) => {
    setTheme(mode)
  }, [])

  const bumpDatasetVersion = useCallback(() => {
    setDatasetVersion((v) => v + 1)
  }, [])

  const activateDatasetById = useCallback(
    async (id: number) => {
      const res = await api.activateDataset(id)
      setActiveDataset(res.dataset)
      await Promise.all([refreshDatasets(), refreshNotifications()])
      setDatasetVersion((v) => v + 1)
      pushToast({
        title: "Dataset Activated",
        message: `Switched workspace to "${res.dataset.name}".`,
        variant: "success",
      })
    },
    [pushToast, refreshDatasets, refreshNotifications]
  )

  const login = useCallback(
    async (email: string, password: string) => {
      const res = await api.login({ email, password })
      setStoredToken(res.token)
      setUser(res.user)
      await Promise.all([refreshDatasets(), refreshNotifications()])
      setDatasetVersion((v) => v + 1)
      pushToast({
        title: "Signed In",
        message: `Welcome back, ${res.user.full_name}`,
        variant: "success",
      })
      return res.user
    },
    [pushToast, refreshDatasets, refreshNotifications]
  )

  const register = useCallback(
    async (payload: {
      email: string
      password: string
      full_name: string
      role?: string
      organization?: string
    }) => {
      const res = await api.register(payload)
      setStoredToken(res.token)
      setUser(res.user)
      await Promise.all([refreshDatasets(), refreshNotifications()])
      setDatasetVersion((v) => v + 1)
      pushToast({
        title: "Account Created",
        message: `Signed in as ${res.user.full_name}`,
        variant: "success",
      })
      return res.user
    },
    [pushToast, refreshDatasets, refreshNotifications]
  )

  const logout = useCallback(async () => {
    try {
      await api.logout()
    } catch {
      // ignore network failure on logout
    }
    setStoredToken(null)
    setUser(null)
    await Promise.all([refreshDatasets(), refreshNotifications()])
    setDatasetVersion((v) => v + 1)
    pushToast({ title: "Signed Out", message: "You are browsing public demo workspace.", variant: "info" })
  }, [pushToast, refreshDatasets, refreshNotifications])

  const updateProfile = useCallback(
    async (payload: {
      full_name: string
      role: string
      organization: string
      bio: string
    }) => {
      const res = await api.updateProfile(payload)
      setUser(res.user)
      await refreshNotifications()
      pushToast({ title: "Profile Saved", message: "Profile changes updated.", variant: "success" })
      return res.user
    },
    [pushToast, refreshNotifications]
  )

  const changePassword = useCallback(
    async (currentPassword: string, newPassword: string) => {
      await api.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      })
      await refreshNotifications()
      pushToast({ title: "Password Updated", message: "Your password was changed securely.", variant: "success" })
    },
    [pushToast, refreshNotifications]
  )

  const setGlobalFilters = useCallback(
    (
      updater:
        | AnalyticsFilterParams
        | ((prev: AnalyticsFilterParams) => AnalyticsFilterParams)
    ) => {
      setGlobalFiltersState((prev) =>
        typeof updater === "function" ? updater(prev) : updater
      )
    },
    []
  )

  const resetFilters = useCallback(() => {
    setGlobalFiltersState({
      platform: "",
      sentiment: "",
      start_date: "",
      end_date: "",
      search: "",
    })
  }, [])

  const markRead = useCallback(
    async (id: number) => {
      await api.markNotificationRead(id)
      await refreshNotifications()
    },
    [refreshNotifications]
  )

  const markAllRead = useCallback(async () => {
    await api.markAllNotificationsRead()
    await refreshNotifications()
  }, [refreshNotifications])

  return (
    <AppContext.Provider
      value={{
        theme,
        toggleTheme,
        setThemeMode,
        user,
        authLoading,
        login,
        register,
        logout,
        updateProfile,
        changePassword,
        datasets,
        activeDataset,
        datasetVersion,
        refreshDatasets,
        activateDatasetById,
        bumpDatasetVersion,
        globalFilters,
        setGlobalFilters,
        resetFilters,
        notifications,
        unreadCount,
        refreshNotifications,
        markRead,
        markAllRead,
        toasts,
        pushToast,
        dismissToast,
        selectedPostId,
        openPostDetail: (id: string) => setSelectedPostId(id),
        closePostDetail: () => setSelectedPostId(null),
        confirmState,
        requestConfirm: (state: ConfirmState) => setConfirmState(state),
        closeConfirm: () => setConfirmState(null),
      }}
    >
      {children}
    </AppContext.Provider>
  )
}

export function useApp(): AppContextValue {
  const ctx = useContext(AppContext)
  if (!ctx) throw new Error("useApp must be used inside AppProvider")
  return ctx
}

