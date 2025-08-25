"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { useAgentStore, useChatStore } from "@/store"
import { 
  Bot, 
  TrendingUp, 
  Search, 
  CheckCircle,
  Circle,
  Zap,
  Users
} from "lucide-react"

const agentIcons = {
  financial: TrendingUp,
  sales_marketing: Users,
  research: Search,
  general: Bot,
}

export function AgentSelector() {
  const { agents, selectedAgent, selectAgent } = useAgentStore()
  const { createSession, currentSession } = useChatStore()

  const handleSelectAgent = (agentId: string) => {
    selectAgent(agentId)
    
    // If there's no current session or agent changed, create new session
    const newAgent = agents.find(a => a.id === agentId)
    if (newAgent && (!currentSession || currentSession.agentId !== agentId)) {
      createSession(agentId)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'online':
        return 'bg-green-500'
      case 'busy':
        return 'bg-yellow-500'
      case 'offline':
        return 'bg-gray-400'
      default:
        return 'bg-gray-400'
    }
  }

  return (
    <Card className="w-full">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center space-x-2">
          <Zap className="h-5 w-5" />
          <span>Select AI Agent</span>
        </CardTitle>
      </CardHeader>
      
      <CardContent className="space-y-3">
        {agents.map((agent) => {
          const IconComponent = agentIcons[agent.type] || Bot
          const isSelected = selectedAgent?.id === agent.id
          
          return (
            <div
              key={agent.id}
              className={`group relative p-4 rounded-lg border cursor-pointer transition-all ${
                isSelected
                  ? 'bg-primary/5 border-primary'
                  : 'hover:bg-accent hover:border-accent-foreground/20'
              } ${agent.status === 'offline' ? 'opacity-60' : ''}`}
              onClick={() => agent.status !== 'offline' && handleSelectAgent(agent.id)}
            >
              <div className="flex items-start space-x-3">
                <div className="relative">
                  <Avatar>
                    <AvatarFallback>
                      <IconComponent className="h-4 w-4" />
                    </AvatarFallback>
                  </Avatar>
                  <div
                    className={`absolute -bottom-1 -right-1 h-3 w-3 rounded-full border-2 border-white ${getStatusColor(
                      agent.status
                    )}`}
                  />
                </div>
                
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-1">
                    <h4 className="font-semibold text-sm">{agent.name}</h4>
                    {isSelected ? (
                      <CheckCircle className="h-4 w-4 text-primary" />
                    ) : (
                      <Circle className="h-4 w-4 text-muted-foreground" />
                    )}
                  </div>
                  
                  <p className="text-xs text-muted-foreground mb-2">
                    {agent.description}
                  </p>
                  
                  <div className="flex items-center justify-between">
                    <Badge
                      variant={agent.status === 'online' ? 'default' : 'secondary'}
                      className="text-xs"
                    >
                      {agent.status}
                    </Badge>
                    
                    <Badge variant="outline" className="text-xs">
                      {agent.type}
                    </Badge>
                  </div>
                  
                  <div className="mt-2">
                    <p className="text-xs text-muted-foreground mb-1">Capabilities:</p>
                    <div className="flex flex-wrap gap-1">
                      {agent.capabilities.slice(0, 3).map((capability) => (
                        <Badge
                          key={capability}
                          variant="outline"
                          className="text-xs px-1 py-0"
                        >
                          {capability}
                        </Badge>
                      ))}
                      {agent.capabilities.length > 3 && (
                        <Badge variant="outline" className="text-xs px-1 py-0">
                          +{agent.capabilities.length - 3} more
                        </Badge>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )
        })}
        
        <div className="pt-2 border-t">
          <p className="text-xs text-muted-foreground text-center">
            More agents coming in Phase 3
          </p>
        </div>
      </CardContent>
    </Card>
  )
}
