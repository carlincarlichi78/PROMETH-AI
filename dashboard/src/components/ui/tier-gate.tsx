import { Lock } from 'lucide-react'
import { Badge } from '@/components/ui/badge'

const TIER_LABEL: Record<string, string> = {
  pro:     'Plan Pro',
  premium: 'Plan Premium',
}

interface TierGateProps {
  feature: string
  requiere: 'pro' | 'premium'
  children: React.ReactNode
}

export function TierGate({ feature: _feature, requiere, children }: TierGateProps) {
  return (
    <div className="relative">
      {children}
      <div className="absolute inset-0 flex items-center justify-center rounded-lg bg-background/80 backdrop-blur-sm">
        <div className="flex flex-col items-center gap-2 text-center p-4">
          <Lock className="h-6 w-6 text-muted-foreground" />
          <p className="text-sm font-medium text-muted-foreground">
            Disponible en{' '}
            <Badge variant="outline" className="ml-1 text-amber-600 border-amber-300">
              {TIER_LABEL[requiere] ?? requiere}
            </Badge>
          </p>
        </div>
      </div>
    </div>
  )
}
