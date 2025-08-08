import { useState, useCallback } from 'react'

export interface Toast {
  id: string
  title?: string
  description?: string
  action?: {
    label: string
    onClick: () => void
  }
  variant?: 'default' | 'destructive'
}

interface ToastState {
  toasts: Toast[]
}

const toastState: ToastState = {
  toasts: []
}

const listeners: Array<(state: ToastState) => void> = []

const setState = (newState: Partial<ToastState>) => {
  Object.assign(toastState, newState)
  listeners.forEach(listener => listener(toastState))
}

let toastCount = 0

export const toast = ({
  title,
  description,
  action,
  variant = 'default',
  ...props
}: Omit<Toast, 'id'>) => {
  const id = (++toastCount).toString()
  
  const newToast: Toast = {
    id,
    title,
    description,
    action,
    variant,
    ...props
  }

  setState({
    toasts: [...toastState.toasts, newToast]
  })

  // Auto dismiss after 5 seconds
  setTimeout(() => {
    setState({
      toasts: toastState.toasts.filter(t => t.id !== id)
    })
  }, 5000)

  return {
    id,
    dismiss: () => {
      setState({
        toasts: toastState.toasts.filter(t => t.id !== id)
      })
    }
  }
}

export const useToast = () => {
  const [state, setState] = useState(toastState)

  const subscribe = useCallback((listener: (state: ToastState) => void) => {
    listeners.push(listener)
    return () => {
      const index = listeners.indexOf(listener)
      if (index > -1) {
        listeners.splice(index, 1)
      }
    }
  }, [])

  useState(() => {
    const unsubscribe = subscribe(setState)
    return unsubscribe
  })

  return {
    ...state,
    toast,
    dismiss: (toastId?: string) => {
      setState({
        toasts: toastState.toasts.filter(t => t.id !== toastId)
      })
    }
  }
} 