import { useQuery, useMutation } from "@tanstack/react-query";
import { SemaforoCard } from "./semaforo-card";

interface Semaforo {
  pytest: { estado: string; ok: number; bugs: number; hace_h: number | null };
  motor: { estado: string; ok: number; bugs: number; hace_min: number | null };
  playwright: { estado: string; ok: number; bugs: number; hace_dias: number | null };
}

interface Sesion {
  id: string; modo: string; trigger: string; estado: string;
  total_ok: number; total_bugs: number; inicio: string | null; fin: string | null;
}

function _token(): string {
  return sessionStorage.getItem("sfce_token") ?? "";
}

function useSemaforo() {
  return useQuery<Semaforo>({
    queryKey: ["testing-semaforo"],
    queryFn: async () => {
      const r = await fetch("/api/testing/semaforo");
      if (!r.ok) throw new Error("Error cargando semáforo");
      return r.json();
    },
    refetchInterval: 60_000,
  });
}

function useSesiones() {
  return useQuery<{ total: number; items: Sesion[] }>({
    queryKey: ["testing-sesiones"],
    queryFn: async () => {
      const r = await fetch("/api/testing/sesiones?limit=10", {
        headers: { Authorization: `Bearer ${_token()}` },
      });
      if (!r.ok) return { total: 0, items: [] };
      return r.json();
    },
    refetchInterval: 30_000,
  });
}

function useEjecutar() {
  return useMutation({
    mutationFn: async (modo: string) => {
      const r = await fetch("/api/testing/ejecutar", {
        method: "POST",
        headers: { Authorization: `Bearer ${_token()}`, "Content-Type": "application/json" },
        body: JSON.stringify({ modo }),
      });
      return r.json();
    },
  });
}

function duracionSesion(s: Sesion): string {
  if (!s.inicio || !s.fin) return s.estado === "en_curso" ? "en curso..." : "-";
  const ms = new Date(s.fin).getTime() - new Date(s.inicio).getTime();
  const seg = Math.round(ms / 1000);
  return seg > 60 ? `${Math.floor(seg / 60)}m ${seg % 60}s` : `${seg}s`;
}

export function TestingPage() {
  const semaforo = useSemaforo();
  const sesiones = useSesiones();
  const ejecutar = useEjecutar();

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">SFCE Health</h1>
        <div className="flex gap-2">
          {(["smoke", "vigilancia", "regression"] as const).map((modo) => (
            <button
              type="button"
              key={modo}
              onClick={() => ejecutar.mutate(modo)}
              disabled={ejecutar.isPending}
              className="px-3 py-1.5 text-xs rounded-lg border border-slate-300 dark:border-slate-600 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors capitalize disabled:opacity-50"
            >
              {modo}
            </button>
          ))}
        </div>
      </div>

      {/* Semáforo 3 capas */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {semaforo.data ? (
          <>
            <SemaforoCard titulo="pytest (CI)" data={semaforo.data.pytest as any} />
            <SemaforoCard titulo="Motor Campo" data={semaforo.data.motor as any} />
            <SemaforoCard titulo="Playwright E2E" data={semaforo.data.playwright as any} />
          </>
        ) : (
          <div className="col-span-3 text-sm text-slate-400 animate-pulse">Cargando semáforo...</div>
        )}
      </div>

      {/* Últimas sesiones */}
      <div>
        <h2 className="text-lg font-semibold mb-3">Últimas sesiones</h2>
        <div className="rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 dark:bg-slate-800">
              <tr className="text-left text-xs text-slate-500 uppercase tracking-wide">
                <th className="px-4 py-3">Modo</th>
                <th className="px-4 py-3">Trigger</th>
                <th className="px-4 py-3">Estado</th>
                <th className="px-4 py-3">OK / Bugs</th>
                <th className="px-4 py-3">Duración</th>
                <th className="px-4 py-3">Inicio</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
              {sesiones.data?.items.map((s) => (
                <tr key={s.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50">
                  <td className="px-4 py-3 font-medium capitalize">{s.modo}</td>
                  <td className="px-4 py-3 text-slate-500">{s.trigger}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                      s.estado === "completado" ? "bg-emerald-100 text-emerald-700" :
                      s.estado === "en_curso" ? "bg-amber-100 text-amber-700" :
                      "bg-red-100 text-red-700"
                    }`}>
                      {s.estado}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-emerald-600">{s.total_ok}</span>
                    {s.total_bugs > 0 && <span className="text-red-500 ml-1">/ {s.total_bugs}</span>}
                  </td>
                  <td className="px-4 py-3 text-slate-500">{duracionSesion(s)}</td>
                  <td className="px-4 py-3 text-slate-400 text-xs">
                    {s.inicio ? new Date(s.inicio).toLocaleString("es") : "-"}
                  </td>
                </tr>
              ))}
              {!sesiones.data?.items.length && (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-slate-400">Sin sesiones todavía</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
