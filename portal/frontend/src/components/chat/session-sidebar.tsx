"use client"

import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { useChatStore, useAgentStore } from "@/store"
import { 
  Plus, 
  MessageSquare, 
  Trash2, 
  Clock 
} from "lucide-react"

export function SessionSidebar() {
  const {
    sessions,
    currentSession,
    createSession,
    setCurrentSession,
    deleteSession,
  } = useChatStore()
  
  const { selectedAgent } = useAgentStore()

  const handleNewSession = () => {
    if (selectedAgent) {
      createSession(selectedAgent.id)
    }
  }

  const formatTime = (date: Date) => {
    return new Intl.DateTimeFormat('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      month: 'short',
      day: 'numeric'
    }).format(new Date(date))
  }

  return (
    <Card className="h-full w-80 flex flex-col">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Chat Sessions</CardTitle>
          <Button
            onClick={handleNewSession}
            size="sm"
            className="h-8 w-8 p-0"
          >
            <Plus className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>

      <CardContent className="flex-1 p-0">
        <ScrollArea className="h-full px-3">
          {sessions.length === 0 ? (
            <div className="text-center py-8">
              <MessageSquare className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground text-sm">
                No chat sessions yet.
                <br />
                Create your first session!
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {sessions.map((session) => (
                <div
                  key={session.id}
                  className={`group relative p-3 rounded-lg border cursor-pointer transition-all hover:bg-accent ${
                    currentSession?.id === session.id
                      ? 'bg-accent border-primary'
                      : 'hover:border-accent-foreground/20'
                  }`}
                  onClick={() => setCurrentSession(session.id)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <h4 className="font-medium text-sm truncate">
                        {session.title}
                      </h4>
                      
                      <div className="flex items-center space-x-2 mt-1">
                        <Clock className="h-3 w-3 text-muted-foreground" />
                        <span className="text-xs text-muted-foreground">
                          {formatTime(session.updatedAt)}
                        </span>
                      </div>
                      
                      <div className="mt-2">
                        <Badge variant="outline" className="text-xs">
                          {session.messages.length} messages
                        </Badge>
                      </div>
                      
                      {session.messages.length > 0 && (
                        <p className="text-xs text-muted-foreground mt-2 line-clamp-2">
                          {session.messages[session.messages.length - 1].content}
                        </p>
                      )}
                    </div>
                    
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
                      onClick={(e) => {
                        e.stopPropagation()
                        deleteSession(session.id)
                      }}
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </ScrollArea>
      </CardContent>
    </Card>
  )
}
