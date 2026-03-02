interface SemaforoData {
  estado: "verde" | "amarillo" | "rojo" | "sin_datos";
  ok: number;
  bugs: number;
  hace_min?: number | null;
  hace_h?: number | null;
  hace_dias?: number | null;
}
interface SemaforoCardProps {
  titulo: string;
  data: SemaforoData;
}

const COLOR = {
  verde: "bg-emerald-500",
  amarillo: "bg-amber-500",
  rojo: "bg-red-500",
  sin_datos: "bg-slate-400",
} as const;

const LABEL = { verde: "Verde", amarillo: "Amarillo", rojo: "Rojo", sin_datos: "Sin datos" };

function tiempoLegible(data: SemaforoData): string {
  if (data.hace_min != null) return `hace ${data.hace_min}min`;
  if (data.hace_h != null) return `hace ${data.hace_h}h`;
  if (data.hace_dias != null) return `hace ${data.hace_dias}d`;
  return "sin datos";
}

export function SemaforoCard({ titulo, data }: SemaforoCardProps) {
  return (
    <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-5 flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <span className={`inline-block w-3 h-3 rounded-full ${COLOR[data.estado]}`} />
        <span className="font-semibold text-sm">{titulo}</span>
        <span className="ml-auto text-xs text-slate-500">{LABEL[data.estado]}</span>
      </div>
      <div className="flex gap-4 text-sm">
        <span className="text-emerald-600 font-medium">{data.ok} OK</span>
        {data.bugs > 0 && <span className="text-red-500 font-medium">{data.bugs} bugs</span>}
      </div>
      <p className="text-xs text-slate-400">{tiempoLegible(data)}</p>
    </div>
  );
}
