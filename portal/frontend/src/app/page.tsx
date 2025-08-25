"use client"

import { useSession } from "next-auth/react"
import { useEffect, useState } from "react"
import { ChatInterface } from "@/components/chat/chat-interface"
import { SessionSidebar } from "@/components/chat/session-sidebar"
import { AgentSelector } from "@/components/chat/agent-selector"
import { Button } from "@/components/ui/button"
import { useChatStore, useAgentStore } from "@/store"
import { signIn, signOut } from "next-auth/react"
import { LogOut, User, BarChart3 } from "lucide-react"
import Link from "next/link"

const isDevelopment = process.env.NEXT_PUBLIC_DEVELOPMENT_MODE === "true"

export default function Dashboard() {
  const { data: session, status } = useSession()
  const { currentSession, createSession } = useChatStore()
  const { selectedAgent } = useAgentStore()
  const [devModeInitialized, setDevModeInitialized] = useState(false)

  // Auto-sign in for development mode
  useEffect(() => {
    if (isDevelopment && status === "unauthenticated" && !devModeInitialized) {
      setDevModeInitialized(true)
      // Force a session creation by calling the callback
      signIn("credentials", { callbackUrl: "/" })
    }
  }, [status, devModeInitialized])

  // Create initial session if none exists
  useEffect(() => {
    if (session && selectedAgent && !currentSession) {
      createSession(selectedAgent.id)
    }
  }, [session, selectedAgent, currentSession, createSession])

  if (status === "loading" || (isDevelopment && !devModeInitialized)) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">
            {isDevelopment ? "Initializing development mode..." : "Loading..."}
          </p>
        </div>
      </div>
    )
  }

  if (!session && !isDevelopment) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
        <div className="text-center">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            Uplevel AI Financial Intelligence
          </h1>
          <p className="text-xl text-gray-600 mb-8">
            Advanced AI-powered financial analysis and insights
          </p>
          <Button onClick={() => signIn("google")} size="lg">
            Sign in with Google
          </Button>
        </div>
      </div>
    )
  }

  // Development mode or authenticated user interface
  const currentUser = session?.user || {
    name: "Development User",
    email: "dev@uplevel.ai"
  }

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <div className="w-80 bg-white border-r border-gray-200 flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-xl font-semibold text-gray-900">
              Uplevel AI
            </h1>
            <div className="flex items-center space-x-2">
              <Link href="/dashboard" className="p-2 hover:bg-gray-100 rounded-lg">
                <BarChart3 className="h-5 w-5 text-gray-600" />
              </Link>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => signOut()}
                className="p-2"
              >
                <LogOut className="h-4 w-4" />
              </Button>
            </div>
          </div>
          
          {/* User Info */}
          <div className="flex items-center space-x-3 p-2 bg-gray-50 rounded-lg">
            <div className="flex items-center justify-center w-8 h-8 bg-blue-600 text-white rounded-full">
              <User className="h-4 w-4" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">
                {currentUser.name}
              </p>
              <p className="text-xs text-gray-500 truncate">
                {currentUser.email}
              </p>
              {isDevelopment && (
                <p className="text-xs text-orange-600 font-medium">
                  Development Mode
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Agent Selector */}
        <div className="p-4">
          <AgentSelector />
        </div>

        {/* Session History */}
        <div className="flex-1 overflow-hidden">
          <SessionSidebar />
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {selectedAgent ? (
          <ChatInterface />
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">
                Welcome to Uplevel AI
              </h2>
              <p className="text-gray-600 mb-8">
                Select an AI agent from the sidebar to begin your analysis.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
