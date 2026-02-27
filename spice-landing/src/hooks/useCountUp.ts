import { useEffect, useState } from 'react'

export function useCountUp(objetivo: number, activo: boolean, duracion = 1500) {
  const [valor, setValor] = useState(0)

  useEffect(() => {
    if (!activo) return

    const inicio = performance.now()
    let frame: number

    const animar = (ahora: number) => {
      const progreso = Math.min((ahora - inicio) / duracion, 1)
      const eased = 1 - Math.pow(1 - progreso, 3)
      setValor(Math.round(eased * objetivo))

      if (progreso < 1) {
        frame = requestAnimationFrame(animar)
      }
    }

    frame = requestAnimationFrame(animar)
    return () => cancelAnimationFrame(frame)
  }, [objetivo, activo, duracion])

  return valor
}
