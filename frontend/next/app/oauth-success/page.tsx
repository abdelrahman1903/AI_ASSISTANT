'use client'

import { useEffect } from 'react'

export default function OAuthSuccess() {
  useEffect(() => {
    window.opener.postMessage("google-auth-success", "*")
    window.close()
  }, [])

  return (
    <div className="flex items-center justify-center min-h-screen">
      <p className="text-foreground">Authentication successful. You may close this window.</p>
    </div>
  )
}
