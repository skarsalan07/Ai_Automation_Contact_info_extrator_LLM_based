import React from 'react'
import Home from './pages/Home.jsx'
import { ToastProvider } from './components/Toast.jsx'

export default function App() {
  return (
    <ToastProvider>
      <Home />
    </ToastProvider>
  )
}
