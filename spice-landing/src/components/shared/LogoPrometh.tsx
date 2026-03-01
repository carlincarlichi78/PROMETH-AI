interface Props {
  size?: 'sm' | 'md' | 'lg'
  showText?: boolean
}

const sizes = {
  sm: { flame: 'w-6 h-8',  text: 'text-lg' },
  md: { flame: 'w-8 h-11', text: 'text-2xl' },
  lg: { flame: 'w-12 h-16',text: 'text-4xl' },
}

export default function LogoPrometh({ size = 'md', showText = true }: Props) {
  const s = sizes[size]
  return (
    <div className="flex items-center gap-2">
      <svg viewBox="0 0 40 56" fill="none" className={`${s.flame} animate-flame`} aria-hidden="true">
        {/* Llama exterior — ámbar */}
        <path d="M20 2C20 2 6 20 6 36c0 11 6 18 14 20 8-2 14-9 14-20 0-16-14-34-14-34z"
          fill="url(#grad-outer)" />
        {/* Llama interior — naranja */}
        <path d="M20 14c0 0-7 12-7 24 0 7 3.5 12 7 14 3.5-2 7-7 7-14 0-12-7-24-7-24z"
          fill="url(#grad-inner)" opacity="0.9" />
        {/* Núcleo brillante */}
        <path d="M20 28c0 0-3 5-3 12 0 4 1.5 7 3 8 1.5-1 3-4 3-8 0-7-3-12-3-12z"
          fill="#fef3c7" opacity="0.8" />
        <defs>
          <linearGradient id="grad-outer" x1="20" y1="2" x2="20" y2="56" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#fbbf24" />
            <stop offset="100%" stopColor="#ea580c" />
          </linearGradient>
          <linearGradient id="grad-inner" x1="20" y1="14" x2="20" y2="52" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#f59e0b" />
            <stop offset="100%" stopColor="#dc2626" />
          </linearGradient>
        </defs>
      </svg>
      {showText && (
        <span className={`font-heading font-bold gradient-text ${s.text} tracking-tight`}>
          PROMETH-AI
        </span>
      )}
    </div>
  )
}
