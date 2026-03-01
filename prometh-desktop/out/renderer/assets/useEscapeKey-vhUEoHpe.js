import { r as reactExports } from "./index-DMbE3NR1.js";
function useEscapeKey(abierto, onCerrar) {
  reactExports.useEffect(() => {
    if (!abierto) return;
    const handler = (e) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onCerrar();
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [abierto, onCerrar]);
}
export {
  useEscapeKey as u
};
