import { create } from 'zustand'

export interface Agent {
  id: string
  name: string
  description: string
  capabilities: string[]
  status: 'online' | 'offline' | 'busy'
  avatar?: string
  endpoint: string
  type: 'financial' | 'sales_marketing' | 'research' | 'general' | 'orchestrator'
}

interface AgentStore {
  // Available agents
  agents: Agent[]
  selectedAgent: Agent | null
  
  // Actions
  setAgents: (agents: Agent[]) => void
  selectAgent: (agentId: string) => void
  updateAgentStatus: (agentId: string, status: Agent['status']) => void
}

// Default agents configuration
const defaultAgents: Agent[] = [
  {
    id: 'central-orchestrator',
    name: 'AI Orchestrator (Multi-Agent)',
    description: 'Intelligent coordinator that combines insights from multiple specialized agents',
    capabilities: [
      'Multi-Agent Coordination',
      'Collaborative Analysis',
      'Cross-Domain Insights', 
      'Complex Query Processing',
      'Integrated Financial + Sales Intelligence',
      'Strategic Recommendations',
      'Workflow Management'
    ],
    status: 'online',
    endpoint: process.env.ORCHESTRATOR_API_URL || 'http://localhost:8001',
    type: 'orchestrator',
  },
  {
    id: 'financial-intelligence',
    name: 'Financial Intelligence Agent',
    description: 'Advanced financial analysis, P&L statements, and business insights',
    capabilities: [
      'Financial Analysis',
      'P&L Statement Generation', 
      'Business Intelligence',
      'Market Research',
      'Risk Assessment'
    ],
    status: 'online',
    endpoint: process.env.FINANCIAL_AGENT_API_URL || 'https://uplevel-financial-agent-834012950450.us-central1.run.app',
    type: 'financial',
  },
  {
    id: 'sales-marketing',
    name: 'Sales & Marketing Intelligence Agent',
    description: 'Sales pipeline management, lead generation, and marketing analytics',
    capabilities: [
      'Lead Management',
      'Sales Pipeline Analysis',
      'Campaign Performance',
      'Customer Segmentation',
      'Revenue Forecasting',
      'Contract Management',
      'Payment Tracking'
    ],
    status: 'online',
    endpoint: process.env.SALES_AGENT_API_URL || 'http://localhost:8003',
    type: 'sales_marketing',
  },
  // Placeholder for future agents
  {
    id: 'research-specialist',
    name: 'Research Specialist',
    description: 'In-depth research and data analysis across various domains',
    capabilities: [
      'Market Research',
      'Competitive Analysis',
      'Industry Reports',
      'Data Mining'
    ],
    status: 'offline',
    endpoint: '', // Will be added in Phase 3
    type: 'research',
  },
]

export const useAgentStore = create<AgentStore>((set, get) => ({
  agents: defaultAgents,
  selectedAgent: defaultAgents[0], // Default to orchestrator

  setAgents: (agents: Agent[]) => {
    set({ agents })
  },

  selectAgent: (agentId: string) => {
    const agent = get().agents.find(a => a.id === agentId)
    if (agent) {
      set({ selectedAgent: agent })
    }
  },

  updateAgentStatus: (agentId: string, status: Agent['status']) => {
    set(state => ({
      agents: state.agents.map(agent =>
        agent.id === agentId ? { ...agent, status } : agent
      ),
      selectedAgent: state.selectedAgent?.id === agentId 
        ? { ...state.selectedAgent, status }
        : state.selectedAgent
    }))
  },
}))
