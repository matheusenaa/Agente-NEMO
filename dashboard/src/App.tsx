import { useEffect } from "react";
import { AppShell } from "@/components/ide/AppShell";
import { useIdeStore } from "@/store/useIdeStore";
import { getAgent } from "@/data/agents";

export function App() {
  useEffect(() => {
    const timer = setTimeout(() => {
      const nemo = getAgent("nemo");
      useIdeStore.getState().notify({
        icon: nemo.icon,
        text: `NEMO IDE online — ${nemo.name} pronto para trabalhar`,
        tone: "ok",
      });
    }, 600);
    return () => clearTimeout(timer);
  }, []);

  return <AppShell />;
}