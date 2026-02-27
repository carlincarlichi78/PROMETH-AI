import { useEffect, useRef, useState } from 'react'

export function useInView(opciones?: IntersectionObserverInit) {
  const ref = useRef<HTMLDivElement>(null)
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const el = ref.current
    if (!el) return

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true)
          observer.unobserve(el)
        }
      },
      { threshold: 0.15, ...opciones }
    )

    observer.observe(el)
    return () => observer.disconnect()
  }, [opciones])

  return { ref, visible }
}
