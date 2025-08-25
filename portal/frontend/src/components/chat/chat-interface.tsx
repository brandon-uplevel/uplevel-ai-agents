"use client"

import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { useChatStore, useAgentStore } from "@/store"
import { Send, Bot, User, Loader2, Workflow } from "lucide-react"

export function ChatInterface() {
  const [inputValue, setInputValue] = useState("")
  const messagesEndRef = useRef<HTMLDivElement>(null)
  
  const { 
    currentSession, 
    addMessage, 
    updateMessage, 
    isLoading,
    setLoading 
  } = useChatStore()
  
  const { selectedAgent } = useAgentStore()

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [currentSession?.messages])

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const handleSendMessage = async () => {
    if (!inputValue.trim() || !selectedAgent || !currentSession) return

    const userMessage = {
      content: inputValue,
      role: 'user' as const,
      agentId: selectedAgent.id,
    }

    // Add user message
    addMessage(userMessage)
    const originalQuery = inputValue
    setInputValue("")
    setLoading(true)

    // Add loading message for assistant
    const loadingMessageId = `msg_loading_${Date.now()}`
    const loadingText = selectedAgent.type === 'orchestrator' 
      ? "Coordinating with specialized agents to provide comprehensive insights..."
      : "Analyzing your request..."

    addMessage({
      content: loadingText,
      role: 'assistant',
      agentId: selectedAgent.id,
      metadata: { loading: true }
    })

    try {
      let requestBody: any
      let responseField = 'response'

      // Handle different API formats
      if (selectedAgent.type === 'orchestrator') {
        // Orchestrator expects OrchestratorQuery format
        requestBody = {
          query: originalQuery,
          session_id: currentSession.id,
          user_id: currentSession.userId || 'frontend_user',
          context: {}
        }
        responseField = 'answer' // Orchestrator returns 'answer' field
      } else {
        // Individual agents expect legacy format
        requestBody = {
          query: originalQuery,
          conversation_id: currentSession.id,
        }
        responseField = 'response' // Individual agents return 'response' field
      }

      // Call the agent API
      const response = await fetch(`${selectedAgent.endpoint}/query`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      })

      if (!response.ok) {
        throw new Error(`API Error: ${response.status}`)
      }

      const data = await response.json()
      
      // Extract response content
      const responseContent = data[responseField] || data.answer || data.response || "I apologize, but I couldn't generate a response."
      
      // For orchestrator responses, include additional metadata in a user-friendly way
      let enhancedContent = responseContent
      if (selectedAgent.type === 'orchestrator' && data.query_type && data.agents_involved) {
        const agentNames = data.agents_involved.map((agent: string) => {
          switch(agent) {
            case 'financial_intelligence': return 'Financial Intelligence'
            case 'sales_marketing': return 'Sales & Marketing'
            default: return agent.replace('_', ' ')
          }
        })
        
        enhancedContent = `${responseContent}\n\n---\n📊 **Query Type**: ${data.query_type}\n🤖 **Agents Consulted**: ${agentNames.join(', ')}`
      }
      
      // Update the loading message with actual response
      updateMessage(loadingMessageId, {
        content: enhancedContent,
        metadata: { 
          loading: false, 
          type: selectedAgent.type === 'orchestrator' ? 'orchestrator' : 'query',
          orchestratorData: selectedAgent.type === 'orchestrator' ? data : undefined
        }
      })

    } catch (error) {
      console.error('Query error:', error)
      
      // Update loading message with error
      updateMessage(loadingMessageId, {
        content: `I apologize, but I encountered an error while processing your request: ${error instanceof Error ? error.message : 'Unknown error'}`,
        metadata: { loading: false, error: true }
      })
    } finally {
      setLoading(false)
    }
  }

  if (!currentSession) {
    return (
      <Card className="flex-1 flex items-center justify-center">
        <CardContent>
          <div className="text-center text-muted-foreground">
            <Bot className="mx-auto h-12 w-12 mb-4" />
            <p>Select an agent to start chatting</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="flex-1 flex flex-col">
      {/* Chat Header */}
      <CardHeader className="border-b">
        <div className="flex items-center space-x-3">
          <Avatar className="h-8 w-8">
            <AvatarFallback>
              {selectedAgent?.type === 'orchestrator' ? <Workflow className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
            </AvatarFallback>
          </Avatar>
          <div className="flex-1">
            <CardTitle className="text-lg">{selectedAgent?.name}</CardTitle>
            <p className="text-sm text-muted-foreground">{selectedAgent?.description}</p>
          </div>
          <Badge variant={selectedAgent?.status === 'online' ? 'default' : 'secondary'}>
            {selectedAgent?.status}
          </Badge>
        </div>
      </CardHeader>

      {/* Messages Area */}
      <ScrollArea className="flex-1 px-4 py-2">
        <div className="space-y-4">
          {currentSession.messages.map((message, index) => (
            <div
              key={index}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'} ${
                message.metadata?.loading ? 'animate-pulse' : ''
              }`}
            >
              <div
                className={`max-w-[80%] rounded-lg px-3 py-2 ${
                  message.role === 'user'
                    ? 'bg-primary text-primary-foreground'
                    : message.metadata?.error
                    ? 'bg-destructive/10 text-destructive border border-destructive/20'
                    : 'bg-muted'
                }`}
              >
                <div className="flex items-start space-x-2">
                  {message.role === 'assistant' && (
                    <Avatar className="h-6 w-6 mt-0.5">
                      <AvatarFallback className="text-xs">
                        {selectedAgent?.type === 'orchestrator' ? <Workflow className="h-3 w-3" /> : <Bot className="h-3 w-3" />}
                      </AvatarFallback>
                    </Avatar>
                  )}
                  <div className="flex-1">
                    <div className="whitespace-pre-wrap text-sm">{message.content}</div>
                    {message.metadata?.loading && (
                      <div className="flex items-center space-x-2 mt-2">
                        <Loader2 className="h-3 w-3 animate-spin" />
                        <span className="text-xs text-muted-foreground">Processing...</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
        <div ref={messagesEndRef} />
      </ScrollArea>

      {/* Input Area */}
      <div className="border-t p-4">
        <div className="flex space-x-2">
          <Input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={selectedAgent?.type === 'orchestrator' 
              ? `Ask for collaborative insights across multiple domains...`
              : `Message ${selectedAgent?.name}...`
            }
            disabled={isLoading}
            className="flex-1"
          />
          <Button
            onClick={handleSendMessage}
            disabled={!inputValue.trim() || isLoading}
            size="icon"
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
        {selectedAgent?.type === 'orchestrator' && (
          <p className="text-xs text-muted-foreground mt-2">
            💡 Try: "Show P&L and create sales strategy", "Analyze revenue trends and marketing ROI", or "Financial forecast with sales pipeline insights"
          </p>
        )}
      </div>
    </div>
  )
}
