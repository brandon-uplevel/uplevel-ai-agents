"use client"

import { signIn, getProviders } from "next-auth/react"
import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

interface Provider {
  id: string
  name: string
}

export default function SignIn() {
  const [providers, setProviders] = useState<Record<string, Provider> | null>(null)

  useEffect(() => {
    const setAuthProviders = async () => {
      const res = await getProviders()
      setProviders(res)
    }
    setAuthProviders()
  }, [])

  if (!providers) {
    return <div>Loading...</div>
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl font-bold">Sign In</CardTitle>
          <CardDescription>
            Sign in to access the Uplevel AI Financial Intelligence Portal
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {Object.values(providers).map((provider: Provider) => (
            <Button
              key={provider.name}
              onClick={() => signIn(provider.id, { callbackUrl: "/" })}
              className="w-full"
            >
              Sign in with {provider.name}
            </Button>
          ))}
        </CardContent>
      </Card>
    </div>
  )
}
