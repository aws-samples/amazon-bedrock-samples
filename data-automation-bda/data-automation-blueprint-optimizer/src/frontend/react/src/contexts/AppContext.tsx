import React, { createContext, useContext, useReducer, ReactNode } from 'react'
import { OptimizerConfig, OptimizerSettings, OptimizerStatus, AppState, Notification } from '../types'



type AppAction =
  | { type: 'SET_CONFIG'; payload: OptimizerConfig }
  | { type: 'SET_SETTINGS'; payload: OptimizerSettings }
  | { type: 'SET_STATUS'; payload: OptimizerStatus }
  | { type: 'SET_CURRENT_LOG'; payload: string | null }
  | { type: 'SET_LOGS'; payload: string[] }
  | { type: 'ADD_NOTIFICATION'; payload: Omit<Notification, 'id'> }
  | { type: 'REMOVE_NOTIFICATION'; payload: string }

const initialState: AppState = {
  config: {
    project_arn: '',
    blueprint_id: '',
    document_name: '',
    dataAutomation_profilearn: '',
    project_stage: 'LIVE',
    input_document: '',
    bda_s3_output_location: '',
    inputs: []
  },
  settings: {
    threshold: 0.6,
    maxIterations: 2,
    model: 'anthropic.claude-3-sonnet-20240229-v1:0',
    useDoc: true,
    clean: true
  },
  status: { status: 'not_running' },
  currentLogFile: null,
  logs: [],
  notifications: []
}

const AppContext = createContext<{
  state: AppState
  dispatch: React.Dispatch<AppAction>
} | null>(null)

function appReducer(state: AppState, action: AppAction): AppState {
  switch (action.type) {
    case 'SET_CONFIG':
      return { ...state, config: action.payload }
    case 'SET_SETTINGS':
      return { ...state, settings: action.payload }
    case 'SET_STATUS':
      return { ...state, status: action.payload }
    case 'SET_CURRENT_LOG':
      return { ...state, currentLogFile: action.payload }
    case 'SET_LOGS':
      return { ...state, logs: action.payload }
    case 'ADD_NOTIFICATION':
      const newNotification: Notification = {
        ...action.payload,
        id: Date.now().toString(),
        dismissible: action.payload.dismissible ?? true,
        autoDismiss: action.payload.autoDismiss ?? (action.payload.type === 'success')
      }
      return { ...state, notifications: [...state.notifications, newNotification] }
    case 'REMOVE_NOTIFICATION':
      return { 
        ...state, 
        notifications: state.notifications.filter(n => n.id !== action.payload) 
      }
    default:
      return state
  }
}

export function AppProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(appReducer, initialState)

  return (
    <AppContext.Provider value={{ state, dispatch }}>
      {children}
    </AppContext.Provider>
  )
}

export function useAppContext() {
  const context = useContext(AppContext)
  if (!context) {
    throw new Error('useAppContext must be used within AppProvider')
  }
  return context
}