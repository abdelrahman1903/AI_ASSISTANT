'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import Link from 'next/link'

export default function HomePage() {
  const router = useRouter()
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('authToken')
    if (token) {
      router.push('/chat')
    } else {
      setIsLoading(false)
    }
  }, [router])

  if (isLoading) {
    return null
  }

  return (
    <main className="h-screen flex items-center justify-center bg-background">
      <div className="w-full max-w-md p-6 space-y-8 text-center">
        <div className="space-y-3">
          <h1 className="text-4xl font-bold text-foreground">Welcome</h1>
          <p className="text-muted-foreground">
            Chat with our AI assistant. Sign in to get started.
          </p>
        </div>

        <div className="space-y-3">
          <Link href="/auth/signin" className="block">
            <Button className="w-full bg-blue-600 hover:bg-blue-700">
              Sign In
            </Button>
          </Link>
          
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-border"></div>
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-background text-muted-foreground">
                New to our app?
              </span>
            </div>
          </div>

          <Link href="/auth/signup" className="block">
            <Button variant="outline" className="w-full">
              Create an Account
            </Button>
          </Link>
        </div>

        <p className="text-xs text-muted-foreground">
          By signing in, you agree to our Terms of Service and Privacy Policy
        </p>
      </div>
    </main>
  )
}
